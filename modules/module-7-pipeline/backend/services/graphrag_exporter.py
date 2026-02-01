"""
GraphRAG Exporter Service.

Exports enriched chunks to text files for GraphRAG indexing.
This enables the dual-index architecture where the same document
feeds both Azure AI Search (vector) and GraphRAG (knowledge graph).
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphRAGExporter:
    """
    Export enriched chunks to text files for GraphRAG indexing.
    
    The key insight is to preserve ALL the rich context we extracted:
    - Figure descriptions from GPT-4V
    - Table markdown
    - Section headers
    - Page context
    
    This allows GraphRAG to build a knowledge graph from the same
    high-quality content we indexed in Azure AI Search.
    """
    
    def __init__(self, graphrag_root: str = "./graphrag-index"):
        """
        Initialize the exporter.
        
        Args:
            graphrag_root: Root directory for GraphRAG project
        """
        self.graphrag_root = Path(graphrag_root)
        self.input_dir = self.graphrag_root / "input"
        self.output_dir = self.graphrag_root / "output"
        
        # Ensure directories exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GraphRAGExporter initialized: {self.graphrag_root}")
    
    def export_chunks_for_graphrag(
        self, 
        chunks: List[Dict[str, Any]], 
        document_name: str,
        include_metadata: bool = True
    ) -> Path:
        """
        Convert enriched chunks to a text file for GraphRAG.
        
        Key insight: Include ALL the rich context we extracted:
        - Figure descriptions from GPT-4V
        - Table markdown
        - Section headers
        - Page context
        
        Args:
            chunks: List of enriched chunk dictionaries
            document_name: Name of the source document
            include_metadata: Whether to include chunk metadata
            
        Returns:
            Path to the created text file
        """
        output_lines = []
        
        # Document header
        output_lines.append(f"# Document: {document_name}")
        output_lines.append(f"# Exported: {datetime.now().isoformat()}")
        output_lines.append(f"# Total chunks: {len(chunks)}")
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")
        
        current_section = None
        current_page = None
        
        # Sort chunks by page number for better context
        sorted_chunks = sorted(
            chunks, 
            key=lambda c: (
                min(c.get("page_numbers", [0]) or [0]),
                c.get("section_header", ""),
                0 if c.get("content_type") == "text" else 1
            )
        )
        
        for chunk in sorted_chunks:
            content_type = chunk.get("content_type", "text")
            section = chunk.get("section_header", "")
            pages = chunk.get("page_numbers", [])
            
            # Add section header if changed
            if section and section != current_section:
                output_lines.append("")
                output_lines.append(f"## {section}")
                output_lines.append("")
                current_section = section
            
            # Add page marker if changed
            if pages and pages != current_page:
                page_str = ", ".join(str(p) for p in pages)
                output_lines.append(f"[Page {page_str}]")
                output_lines.append("")
                current_page = pages
            
            # Format based on content type
            if content_type == "text":
                output_lines.append(chunk.get("content", ""))
                output_lines.append("")
                
            elif content_type == "table":
                output_lines.append("### Table")
                output_lines.append("")
                
                # Prefer markdown format for GraphRAG
                table_content = chunk.get("table_markdown") or chunk.get("content", "")
                output_lines.append(table_content)
                output_lines.append("")
                
            elif content_type == "figure":
                output_lines.append("### Figure")
                output_lines.append("")
                
                # Include ALL the rich figure context
                if chunk.get("figure_caption"):
                    output_lines.append(f"**Caption:** {chunk['figure_caption']}")
                
                # THIS IS THE KEY: Include GPT-4V description!
                if chunk.get("figure_description"):
                    output_lines.append(f"**AI Description:** {chunk['figure_description']}")
                
                # Include surrounding context for relationship extraction
                if chunk.get("surrounding_text"):
                    output_lines.append(f"**Page Context:** {chunk['surrounding_text']}")
                
                # Also include any content field
                content = chunk.get("content", "")
                if content and "Figure Description:" not in content:
                    output_lines.append(f"**Content:** {content}")
                
                output_lines.append("")
            
            else:
                # Unknown type - just include content
                output_lines.append(f"[{content_type}]")
                output_lines.append(chunk.get("content", ""))
                output_lines.append("")
        
        # Write to file
        safe_name = self._sanitize_filename(document_name)
        output_path = self.input_dir / f"{safe_name}.txt"
        
        full_content = "\n".join(output_lines)
        output_path.write_text(full_content, encoding="utf-8")
        
        logger.info(f"Exported {len(chunks)} chunks to: {output_path}")
        logger.info(f"   File size: {len(full_content):,} characters")
        
        return output_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """Create a safe filename for GraphRAG input."""
        # Remove extension
        name = Path(filename).stem
        # Replace unsafe characters
        safe = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        safe = "".join(c for c in safe if c.isalnum() or c in "_-")
        return safe[:100]  # Limit length
    
    def create_graphrag_config(
        self,
        azure_openai_endpoint: str,
        azure_openai_api_key: str,
        chat_model: str = "gpt-4.1",
        embedding_model: str = "text-embedding-3-large",
        entity_types: Optional[List[str]] = None
    ) -> Path:
        """
        Create GraphRAG configuration files.
        
        Args:
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_api_key: Azure OpenAI API key
            chat_model: Chat model deployment name
            embedding_model: Embedding model deployment name
            entity_types: Custom entity types to extract
            
        Returns:
            Path to settings.yaml
        """
        if entity_types is None:
            # Default entity types for technical documents
            entity_types = [
                "STATION",
                "LOCATION",
                "LINE",
                "SERVICE",
                "INFRASTRUCTURE",
                "ORGANIZATION",
                "PERSON",
                "DATE",
                "METRIC"
            ]
        
        # Create settings.yaml
        settings_content = f"""# GraphRAG Configuration
# Auto-generated by RAG Workshop Pipeline

models:
  default_chat_model:
    type: azure_openai_chat
    model: {chat_model}
    api_base: {azure_openai_endpoint}
    api_version: "2024-12-01-preview"
    deployment_name: {chat_model}
    api_key: ${{GRAPHRAG_API_KEY}}
    auth_type: api_key
    requests_per_minute: 60
    tokens_per_minute: 80000
    max_tokens: 4000
    temperature: 0

  default_embedding_model:
    type: azure_openai_embedding
    model: {embedding_model}
    api_base: {azure_openai_endpoint}
    api_version: "2024-12-01-preview"
    deployment_name: {embedding_model}
    api_key: ${{GRAPHRAG_API_KEY}}
    auth_type: api_key
    requests_per_minute: 120
    tokens_per_minute: 120000

input:
  type: file
  file_type: text
  base_dir: input

chunking:
  type: tokens
  size: 1200
  overlap: 100

extract_graph:
  entity_types:
{chr(10).join(f'    - {et}' for et in entity_types)}
  max_gleanings: 1

cluster_graph:
  max_cluster_size: 10

community_reports:
  max_length: 2000
  max_input_length: 8000

output:
  type: file
  base_dir: output

reporting:
  type: file
  base_dir: output/reports

snapshots:
  graphml: true
"""
        
        settings_path = self.graphrag_root / "settings.yaml"
        settings_path.write_text(settings_content, encoding="utf-8")
        
        # Create .env file for GraphRAG
        env_content = f"""GRAPHRAG_API_KEY={azure_openai_api_key}
GRAPHRAG_API_BASE={azure_openai_endpoint}
"""
        env_path = self.graphrag_root / ".env"
        env_path.write_text(env_content, encoding="utf-8")
        
        logger.info(f"Created GraphRAG config at: {settings_path}")
        
        return settings_path
    
    def run_graphrag_indexing(self, timeout: int = 600) -> Dict[str, Any]:
        """
        Run GraphRAG indexing on the exported documents.
        
        ⚠️ WARNING: This is expensive! Each document requires many LLM calls
        for entity extraction, relationship extraction, and community summarization.
        
        Args:
            timeout: Maximum time in seconds to wait for indexing
            
        Returns:
            Dict with indexing results
        """
        logger.info("🚀 Starting GraphRAG indexing...")
        logger.info("   ⚠️ This may take several minutes and use significant tokens!")
        
        lock_file = self.graphrag_root / ".indexing_in_progress"
        
        try:
            # Create lock file to indicate indexing is in progress
            lock_file.write_text(f"Started: {datetime.now().isoformat()}")
            
            result = subprocess.run(
                [sys.executable, "-m", "graphrag", "index", "--root", str(self.graphrag_root)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.graphrag_root)
            )
            
            if result.returncode == 0:
                logger.info("✅ GraphRAG indexing complete!")
                
                # Check output files
                output_files = list(self.output_dir.glob("*.parquet"))
                
                return {
                    "success": True,
                    "output_files": [str(f.name) for f in output_files],
                    "stdout": result.stdout[-2000:] if result.stdout else "",
                    "indexing_complete": True
                }
            else:
                logger.error(f"❌ GraphRAG indexing failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "stdout": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"GraphRAG indexing timed out after {timeout} seconds")
            return {
                "success": False,
                "error": f"Indexing timed out after {timeout} seconds"
            }
        except Exception as e:
            logger.error(f"GraphRAG indexing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Always remove lock file when done
            if lock_file.exists():
                lock_file.unlink()
    
    def get_index_status(self) -> Dict[str, Any]:
        """
        Check the status of GraphRAG index.
        
        Returns:
            Dict with index status information
        """
        status = {
            "graphrag_root": str(self.graphrag_root),
            "input_documents": 0,
            "output_exists": False,
            "parquet_files": [],
            "entities_count": 0,
            "relationships_count": 0,
            "communities_count": 0,
            "has_parquet": False,
            "ready": False,
            "is_indexing": False,
            "indexing_progress": None
        }
        
        # Check for indexing lock file
        lock_file = self.graphrag_root / ".indexing_in_progress"
        if lock_file.exists():
            status["is_indexing"] = True
            try:
                status["indexing_progress"] = lock_file.read_text().strip()
            except Exception:
                status["indexing_progress"] = "Indexing in progress..."
        
        # Count input documents
        if self.input_dir.exists():
            status["input_documents"] = len(list(self.input_dir.glob("*.txt")))
        
        # Check output
        if self.output_dir.exists():
            status["output_exists"] = True
            parquet_files = list(self.output_dir.glob("*.parquet"))
            status["parquet_files"] = [f.name for f in parquet_files]
            status["has_parquet"] = len(parquet_files) > 0
            
            # Try to count entities and relationships
            try:
                import pandas as pd
                
                entities_path = self.output_dir / "entities.parquet"
                if entities_path.exists():
                    entities_df = pd.read_parquet(entities_path)
                    status["entities_count"] = len(entities_df)
                
                relationships_path = self.output_dir / "relationships.parquet"
                if relationships_path.exists():
                    relationships_df = pd.read_parquet(relationships_path)
                    status["relationships_count"] = len(relationships_df)
                
                communities_path = self.output_dir / "communities.parquet"
                if communities_path.exists():
                    communities_df = pd.read_parquet(communities_path)
                    status["communities_count"] = len(communities_df)
                
                # Ready if we have entities and relationships
                status["ready"] = (
                    status["entities_count"] > 0 and 
                    status["relationships_count"] > 0
                )
            except Exception as e:
                logger.warning(f"Could not read Parquet files: {e}")
        
        return status
    
    def clear_index(self) -> bool:
        """
        Clear the GraphRAG index (both input and output).
        
        Returns:
            True if successful
        """
        import shutil
        
        try:
            if self.input_dir.exists():
                shutil.rmtree(self.input_dir)
                self.input_dir.mkdir(parents=True, exist_ok=True)
            
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            
            logger.info("Cleared GraphRAG index")
            return True
        except Exception as e:
            logger.error(f"Failed to clear GraphRAG index: {e}")
            return False
