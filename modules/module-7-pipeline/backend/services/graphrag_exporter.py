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
    
    def start_graphrag_indexing_background(self) -> Dict[str, Any]:
        """
        Start GraphRAG indexing in the background (non-blocking).
        
        This starts the indexing process and returns immediately.
        Use get_index_status() to check progress.
        
        Returns:
            Dict with status info
        """
        logger.info("🚀 Starting GraphRAG indexing in background...")
        
        lock_file = self.graphrag_root / ".indexing_in_progress"
        
        # Check if already indexing
        if lock_file.exists():
            return {
                "success": False,
                "error": "Indexing already in progress",
                "is_indexing": True
            }
        
        try:
            # Create lock file
            lock_file.write_text(f"Started: {datetime.now().isoformat()}")
            
            # Start process in background (non-blocking)
            log_file = self.graphrag_root / "logs" / "indexing-engine.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use Popen for non-blocking execution
            with open(log_file, "a") as log_out:
                process = subprocess.Popen(
                    [sys.executable, "-m", "graphrag", "index", "--root", str(self.graphrag_root)],
                    stdout=log_out,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.graphrag_root),
                    start_new_session=True  # Detach from parent process
                )
            
            logger.info(f"✅ GraphRAG indexing started in background (PID: {process.pid})")
            
            return {
                "success": True,
                "message": "Indexing started in background",
                "pid": process.pid,
                "is_indexing": True
            }
            
        except Exception as e:
            logger.error(f"Failed to start GraphRAG indexing: {e}")
            if lock_file.exists():
                lock_file.unlink()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_indexing_progress(self) -> Dict[str, Any]:
        """
        Parse the indexing log to extract real-time progress.
        
        Returns:
            Dict with current_step, current_progress, total_items, percentage, eta_minutes
        """
        progress = {
            "current_step": None,
            "current_progress": 0,
            "total_items": 0,
            "percentage": 0,
            "eta_minutes": None,
            "steps_completed": [],
            "steps_remaining": []
        }
        
        # Define the workflow steps and their approximate weights (time %)
        all_steps = [
            ("load_input_documents", 1),
            ("create_base_text_units", 2),
            ("create_final_documents", 1),
            ("extract_graph", 40),  # This is the slowest step
            ("finalize_graph", 2),
            ("extract_covariates", 2),
            ("create_communities", 5),
            ("create_final_text_units", 2),
            ("create_community_reports", 35),  # Second slowest
            ("generate_text_embeddings", 10)
        ]
        step_names = [s[0] for s in all_steps]
        step_weights = {s[0]: s[1] for s in all_steps}
        total_weight = sum(s[1] for s in all_steps)
        
        log_file = self.graphrag_root / "logs" / "indexing-engine.log"
        if not log_file.exists():
            return progress
        
        try:
            import re
            from datetime import datetime
            
            # Read last 500 lines of log
            with open(log_file, 'r') as f:
                lines = f.readlines()[-500:]
            
            completed_steps = set()
            current_step = None
            current_item = 0
            total_items = 0
            first_timestamp = None
            last_timestamp = None
            
            for line in lines:
                # Parse timestamp
                ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if ts_match:
                    try:
                        ts = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if first_timestamp is None:
                            first_timestamp = ts
                        last_timestamp = ts
                    except:
                        pass
                
                # Check for workflow completion
                if "Workflow complete:" in line or "completed successfully" in line:
                    for step in step_names:
                        if step in line:
                            completed_steps.add(step)
                            break
                
                # Check for workflow start
                if "Workflow started:" in line:
                    for step in step_names:
                        if step in line:
                            current_step = step
                            break
                
                # Check for progress updates (e.g., "extract graph progress: 45/141")
                progress_match = re.search(r'progress[:\s]+(\d+)/(\d+)', line, re.IGNORECASE)
                if progress_match:
                    current_item = int(progress_match.group(1))
                    total_items = int(progress_match.group(2))
                    
                    # Map log messages to step names
                    line_lower = line.lower()
                    if "entity" in line_lower or "relationship" in line_lower or "summarize" in line_lower:
                        current_step = "extract_graph"
                    elif "community report" in line_lower:
                        current_step = "create_community_reports"
                    elif "embedding" in line_lower:
                        current_step = "generate_text_embeddings"
                    elif "covariate" in line_lower:
                        current_step = "extract_covariates"
                    elif "communit" in line_lower:
                        current_step = "create_communities"
                    else:
                        # Fallback: detect which step from step name patterns
                        for step in step_names:
                            step_readable = step.replace('_', ' ')
                            if step_readable in line_lower:
                                current_step = step
                                break
            
            # Calculate overall progress
            weight_completed = 0
            for step in completed_steps:
                weight_completed += step_weights.get(step, 0)
            
            # Add partial progress for current step
            if current_step and current_step not in completed_steps and total_items > 0:
                step_weight = step_weights.get(current_step, 0)
                partial_weight = step_weight * (current_item / total_items)
                weight_completed += partial_weight
            
            overall_percentage = int((weight_completed / total_weight) * 100)
            
            # Calculate ETA
            eta_minutes = None
            if first_timestamp and last_timestamp and overall_percentage > 0:
                elapsed_seconds = (last_timestamp - first_timestamp).total_seconds()
                if elapsed_seconds > 30 and overall_percentage > 5:  # Need some data points
                    remaining_pct = 100 - overall_percentage
                    eta_seconds = (elapsed_seconds / overall_percentage) * remaining_pct
                    eta_minutes = round(eta_seconds / 60, 1)
            
            # Build steps lists
            progress["steps_completed"] = [s for s in step_names if s in completed_steps]
            progress["steps_remaining"] = [s for s in step_names if s not in completed_steps]
            progress["current_step"] = current_step
            progress["current_progress"] = current_item
            progress["total_items"] = total_items
            progress["percentage"] = min(overall_percentage, 99)  # Cap at 99 until truly done
            progress["eta_minutes"] = eta_minutes
            
        except Exception as e:
            logger.warning(f"Failed to parse indexing progress: {e}")
        
        return progress

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
            "indexing_progress": None,
            "progress_detail": None
        }
        
        # Check for indexing lock file
        lock_file = self.graphrag_root / ".indexing_in_progress"
        if lock_file.exists():
            status["is_indexing"] = True
            try:
                status["indexing_progress"] = lock_file.read_text().strip()
            except Exception:
                status["indexing_progress"] = "Indexing in progress..."
            
            # Parse detailed progress from log
            status["progress_detail"] = self._parse_indexing_progress()
        
        # Count input documents and collect names
        if self.input_dir.exists():
            input_files = sorted(self.input_dir.glob("*.txt"))
            status["input_documents"] = len(input_files)
            status["input_document_names"] = [
                f.stem for f in input_files  # filename without .txt extension
            ]
        
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
                
                # Check for community_reports - required for global search
                community_reports_path = self.output_dir / "community_reports.parquet"
                has_community_reports = community_reports_path.exists()
                
                # Ready only if we have ALL required files including community_reports
                status["ready"] = (
                    status["entities_count"] > 0 and 
                    status["relationships_count"] > 0 and
                    has_community_reports
                )
            except Exception as e:
                logger.warning(f"Could not read Parquet files: {e}")
        
        return status
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Analyze token usage from GraphRAG cache files.
        
        GraphRAG caches every LLM and embedding call as JSON files.
        Each cache entry contains the full OpenAI response including
        token usage stats. This method aggregates those stats to show
        how many tokens were consumed during indexing.
        
        Returns per-category totals (extract_graph, summarize_descriptions,
        community_reporting, text_embedding) and per-document proportional
        estimates based on text_unit counts.
        """
        cache_dir = self.graphrag_root / "cache"
        
        result: Dict[str, Any] = {
            "available": False,
            "categories": {},
            "totals": {
                "llm_prompt_tokens": 0,
                "llm_completion_tokens": 0,
                "llm_total_tokens": 0,
                "llm_calls": 0,
                "embedding_tokens": 0,
                "embedding_calls": 0,
                "grand_total_tokens": 0,
            },
            "per_document": [],
        }
        
        if not cache_dir.exists():
            return result
        
        result["available"] = True
        
        # 1. Aggregate LLM token usage per category
        llm_categories = ["extract_graph", "summarize_descriptions", "community_reporting"]
        for cat in llm_categories:
            cat_dir = cache_dir / cat
            if not cat_dir.exists():
                continue
            
            prompt_tokens = 0
            completion_tokens = 0
            call_count = 0
            
            for f in cat_dir.iterdir():
                try:
                    with open(f) as fh:
                        d = json.load(fh)
                    usage = d.get("result", {}).get("response", {}).get("usage", {})
                    prompt_tokens += usage.get("prompt_tokens", 0)
                    completion_tokens += usage.get("completion_tokens", 0)
                    call_count += 1
                except (json.JSONDecodeError, OSError):
                    continue
            
            cat_info = {
                "calls": call_count,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            result["categories"][cat] = cat_info
            result["totals"]["llm_prompt_tokens"] += prompt_tokens
            result["totals"]["llm_completion_tokens"] += completion_tokens
            result["totals"]["llm_total_tokens"] += prompt_tokens + completion_tokens
            result["totals"]["llm_calls"] += call_count
        
        # 2. Aggregate embedding token usage
        emb_dir = cache_dir / "text_embedding"
        if emb_dir.exists():
            emb_tokens = 0
            emb_calls = 0
            for f in emb_dir.iterdir():
                try:
                    with open(f) as fh:
                        d = json.load(fh)
                    usage = d.get("result", {}).get("response", {}).get("usage", {})
                    # Embedding responses use total_tokens (= prompt_tokens, no completion)
                    emb_tokens += usage.get("total_tokens", 0) or usage.get("prompt_tokens", 0)
                    emb_calls += 1
                except (json.JSONDecodeError, OSError):
                    continue
            
            result["categories"]["text_embedding"] = {
                "calls": emb_calls,
                "total_tokens": emb_tokens,
            }
            result["totals"]["embedding_tokens"] = emb_tokens
            result["totals"]["embedding_calls"] = emb_calls
        
        result["totals"]["grand_total_tokens"] = (
            result["totals"]["llm_total_tokens"] + result["totals"]["embedding_tokens"]
        )
        
        # 3. Per-document proportional breakdown
        try:
            import pandas as pd
            
            docs_path = self.output_dir / "documents.parquet"
            tu_path = self.output_dir / "text_units.parquet"
            
            if docs_path.exists() and tu_path.exists():
                docs = pd.read_parquet(docs_path)
                tu = pd.read_parquet(tu_path)
                
                total_chunks = len(tu)
                total_llm = result["totals"]["llm_total_tokens"]
                total_emb = result["totals"]["embedding_tokens"]
                
                per_doc = tu.groupby("document_id").agg(
                    chunks=("id", "count"),
                    chunk_tokens=("n_tokens", "sum"),
                ).reset_index()
                
                per_doc = per_doc.merge(
                    docs[["id", "title"]], left_on="document_id", right_on="id", how="left"
                )
                
                for _, row in per_doc.iterrows():
                    ratio = row["chunks"] / total_chunks if total_chunks > 0 else 0
                    result["per_document"].append({
                        "title": row["title"],
                        "chunks": int(row["chunks"]),
                        "chunk_tokens": int(row["chunk_tokens"]),
                        "estimated_llm_tokens": int(total_llm * ratio),
                        "estimated_embedding_tokens": int(total_emb * ratio),
                        "estimated_total_tokens": int((total_llm + total_emb) * ratio),
                    })
                
                # Sort by total tokens descending
                result["per_document"].sort(key=lambda x: x["estimated_total_tokens"], reverse=True)
        except Exception as e:
            logger.warning(f"Could not compute per-document token usage: {e}")
        
        return result

    def clear_index(self, clear_cache: bool = True) -> bool:
        """
        Clear the GraphRAG index (input, output, and cache).
        Also removes any indexing lock files to cancel in-progress builds.
        
        Args:
            clear_cache: If True, also delete the LLM/embedding cache files.
                         Set to True for a full reset.
        
        Returns:
            True if successful
        """
        import shutil
        import time
        
        errors = []
        
        # Remove indexing lock file if it exists (cancel in-progress indexing)
        lock_file = self.graphrag_root / ".indexing_in_progress"
        if lock_file.exists():
            try:
                lock_file.unlink()
                logger.info("Removed indexing lock file")
            except OSError as e:
                errors.append(f"lock file: {e}")
        
        # Remove indexing log file
        log_file = self.graphrag_root / "indexing.log"
        if log_file.exists():
            try:
                log_file.unlink()
                logger.info("Removed indexing log file")
            except OSError as e:
                errors.append(f"log file: {e}")
        
        # Clear input directory
        if self.input_dir.exists():
            try:
                shutil.rmtree(self.input_dir, ignore_errors=True)
                self.input_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cleared input directory")
            except OSError as e:
                errors.append(f"input dir: {e}")
        
        # Clear output directory (may contain lancedb with locked files)
        if self.output_dir.exists():
            try:
                shutil.rmtree(self.output_dir, ignore_errors=False)
                logger.info("Cleared output directory")
            except OSError:
                # LanceDB may hold file locks — wait briefly and retry
                logger.warning("Output dir locked, retrying after 1s...")
                time.sleep(1)
                try:
                    shutil.rmtree(self.output_dir, ignore_errors=True)
                    logger.info("Cleared output directory (retry with ignore_errors)")
                except OSError as e2:
                    errors.append(f"output dir: {e2}")
        
        # Clear cache directory (LLM + embedding response caches)
        if clear_cache:
            cache_dir = self.graphrag_root / "cache"
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    logger.info("Cleared cache directory")
                except OSError as e:
                    errors.append(f"cache dir: {e}")
        
        if errors:
            logger.error(f"Partial clear - errors: {errors}")
            return False
        
        logger.info("Cleared GraphRAG index completely (input + output + cache)")
        return True
