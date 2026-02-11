"""
Document Processor Service.
Orchestrates DI or CU + GPT-4 Vision for document processing.

Supports two modes controlled by settings.document_processing_mode:
- "di": Use Azure Document Intelligence (default)
- "cu": Use Azure Content Understanding (provides markdown output)
"""

import io
import logging
import base64
import re
from typing import List, Dict, Any, Optional

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential
    DI_AVAILABLE = True
except ImportError:
    DI_AVAILABLE = False

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config.settings import get_settings
from services.blob_service import BlobService
from services.search_service import SearchService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processing with DI (bounding boxes) + GPT-4V (figure descriptions).
    
    Flow:
    1. DI extracts layout, tables, figures with bounding boxes
    2. Figures are cropped and stored in blob
    3. GPT-4 Vision generates semantic descriptions for figures
    4. Content is chunked by type (text, table, figure)
    5. Chunks are indexed in Azure AI Search
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_service = BlobService()
        self.search_service = SearchService()
        self._di_client = None
        self._openai_client = None
        logger.info(f"DocumentProcessor initialized (DI: {DI_AVAILABLE}, Pillow: {PILLOW_AVAILABLE}, OpenAI: {OPENAI_AVAILABLE})")
    
    @property
    def openai_client(self):
        """Get Azure OpenAI client for vision."""
        if not OPENAI_AVAILABLE:
            return None
        
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-10-21",
                azure_endpoint=self.settings.azure_openai_endpoint
            )
        return self._openai_client
    
    @property
    def di_client(self):
        """Get Document Intelligence client."""
        if not DI_AVAILABLE:
            raise RuntimeError("Azure Document Intelligence SDK not installed")
        
        if self._di_client is None:
            logger.info(f"Creating DI client for {self.settings.azure_document_intelligence_endpoint}")
            self._di_client = DocumentIntelligenceClient(
                endpoint=self.settings.azure_document_intelligence_endpoint,
                credential=AzureKeyCredential(self.settings.azure_document_intelligence_key)
            )
        return self._di_client
    
    @staticmethod
    def _sanitize_doc_id(filename: str) -> str:
        """Generate an Azure AI Search-safe document ID from a filename.
        
        Azure AI Search keys can only contain letters, digits,
        underscore (_), dash (-), or equal sign (=).
        """
        # Remove extension, replace dots and spaces with underscores
        doc_id = filename.replace(".", "_").replace(" ", "_")
        # Strip any remaining invalid characters (e.g. parentheses, brackets, etc.)
        doc_id = re.sub(r'[^a-zA-Z0-9_\-=]', '', doc_id)
        return doc_id[:50]

    async def _generate_figure_description(
        self,
        image_bytes: bytes,
        caption: Optional[str] = None,
        page_context: Optional[str] = None,
        section_context: Optional[str] = None
    ) -> str:
        """
        Generate semantic description for a figure using GPT-4 Vision.
        
        Args:
            image_bytes: PNG image data
            caption: Optional existing caption from DI
            page_context: Optional text context from the same page
            section_context: Optional section header this figure belongs to
            
        Returns:
            Description string for the figure
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available for figure description")
            return caption or ""
        
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Build GENERIC context-aware prompt (works for any document/language)
            prompt_parts = [
                "Describe this image in detail for search indexing. Focus on:",
                "1. What type of image (map, diagram, chart, photo, schematic, table)",
                "2. All visible text, labels, numbers, and identifiers",
                "3. Key entities: place names, station names, product names, people, dates",
                "4. The purpose or meaning of the image in context",
                "5. Relationships between entities — how are elements connected, grouped, or ordered?",
                "   Write explicit sentences like: '[Entity A] is connected to [Entity B]'",
                "",
                "Write the description in the SAME LANGUAGE as the text visible in the image.",
                "If the image contains Hebrew text, respond in Hebrew.",
                "If the image contains English text, respond in English.",
                "Extract ALL numbers and identifiers visible in the image."
            ]
            
            # Add section context - this helps GPT-4V understand what the figure is about
            if section_context:
                prompt_parts.insert(0, f"DOCUMENT SECTION: {section_context}")
                prompt_parts.insert(1, "This image is part of the above section. Keep this context in mind.\n")
            
            if caption:
                prompt_parts.append(f"\nExisting caption: {caption}")
            
            if page_context:
                prompt_parts.append(f"\nPage context: {page_context[:500]}")
            
            prompt = "\n".join(prompt_parts)
            
            response = self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,  # gpt-4.1 or gpt-4o (both support vision)
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000  # Increased for complex figures with many entities
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"Generated figure description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.warning(f"Failed to generate figure description: {e}")
            return caption or ""
    
    async def process_document(
        self,
        blob_path: str,
        content: bytes,
        filename: str,
        use_di: bool = True,
        export_to_graphrag: bool = True,
        auto_index_graphrag: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Process a document end-to-end with DUAL-INDEX support.
        
        Pipeline:
        1. Analyze with Document Intelligence (extracts figures with bounding boxes)
        2. Crop figures from PDF using bounding boxes
        3. Generate GPT-4V descriptions for figures WITH document context
        4. Upload cropped figures to Blob Storage
        5. Create context-aware chunks (text + tables + figures)
        6. Generate embeddings and index in Azure AI Search
        7. [NEW] Export chunks for GraphRAG indexing (if enabled)
        
        Args:
            blob_path: Path where document is stored in blob
            content: Document content as bytes
            filename: Original filename
            use_di: If True, use DI + GPT-4V. If False, fallback to CU.
            export_to_graphrag: If True, also export chunks for GraphRAG indexing
            auto_index_graphrag: If provided, overrides settings.graphrag_auto_index
            
        Returns:
            Processing result with counts
        """
        # Store the auto_index override for later use
        self._auto_index_graphrag_override = auto_index_graphrag
        if not use_di:
            # Fallback to Content Understanding
            logger.info(f"Processing document with Content Understanding: {filename}")
            from services.content_understanding_processor import ContentUnderstandingProcessor
            cu_processor = ContentUnderstandingProcessor()
            result = await cu_processor.process_document(blob_path, content, filename)
            return result
        
        # Use DI + GPT-4V pipeline
        logger.info(f"Processing document with DI + GPT-4V pipeline: {filename}")
        
        doc_id = self._sanitize_doc_id(filename)
        
        # 1. Analyze with Document Intelligence
        logger.info("Step 1: Analyzing with Document Intelligence...")
        di_result = await self._analyze_with_di(content, filename)
        
        # Save DI result for debugging
        await self._save_di_result(di_result, filename)
        
        logger.info(f"   ✅ Pages: {di_result.get('page_count', 0)}")
        logger.info(f"   ✅ Paragraphs: {len(di_result.get('paragraphs', []))}")
        logger.info(f"   ✅ Tables: {len(di_result.get('tables', []))}")
        logger.info(f"   ✅ Figures: {len(di_result.get('figures', []))}")
        
        # 2. Extract figures (crop + GPT-4V descriptions + blob upload)
        logger.info("Step 2: Extracting figures with GPT-4V descriptions...")
        figures = await self._extract_figures(content, di_result, doc_id, filename)
        logger.info(f"   ✅ Processed {len(figures)} figures")
        
        # 3. Create context-aware chunks
        logger.info("Step 3: Creating context-aware chunks...")
        chunks = await self._create_chunks(di_result, doc_id, filename, blob_path, figures)
        
        text_chunks = sum(1 for c in chunks if c['content_type'] == 'text')
        table_chunks = sum(1 for c in chunks if c['content_type'] == 'table')
        figure_chunks = sum(1 for c in chunks if c['content_type'] == 'figure')
        logger.info(f"   ✅ Created {len(chunks)} chunks (text: {text_chunks}, tables: {table_chunks}, figures: {figure_chunks})")
        
        # 4. Generate embeddings and index to Azure AI Search
        logger.info("Step 4: Generating embeddings and indexing to Azure AI Search...")
        await self.search_service.index_chunks(chunks)
        logger.info(f"   ✅ Indexed {len(chunks)} chunks to Azure AI Search")
        
        result = {
            "doc_id": doc_id,
            "filename": filename,
            "page_count": di_result.get("page_count", 0),
            "chunks_created": len(chunks),
            "text_chunks": text_chunks,
            "table_chunks": table_chunks,
            "figure_chunks": figure_chunks,
            "figures_processed": len(figures),
            "figures_extracted": len(figures),  # Alias for API compatibility
            "processing_mode": "di_gpt4v"
        }
        
        # 5. [NEW] Export for GraphRAG (DUAL-INDEX)
        if export_to_graphrag and self.settings.graphrag_enabled:
            logger.info("Step 5: Exporting chunks for GraphRAG...")
            try:
                graphrag_result = await self._export_to_graphrag(chunks, filename)
                result["graphrag_exported"] = True
                result["graphrag_path"] = graphrag_result.get("path", "")
                logger.info(f"   ✅ Exported to GraphRAG: {result['graphrag_path']}")
            except Exception as e:
                logger.warning(f"   ⚠️ GraphRAG export failed: {e}")
                result["graphrag_exported"] = False
                result["graphrag_error"] = str(e)
        
        logger.info(f"✅ Document processing complete: {result}")
        return result
    
    async def process_image(
        self,
        blob_path: str,
        content: bytes,
        filename: str,
        export_to_graphrag: bool = True,
        auto_index_graphrag: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Process an image file with OCR + GPT-4V Vision description.
        
        Pipeline:
        1. Run OCR with Document Intelligence (prebuilt-read model)
        2. Generate rich description with GPT-4V Vision
        3. Upload image to Blob Storage
        4. Create a single "figure" chunk with combined content
        5. Generate embedding and index to Azure AI Search
        6. Optionally export for GraphRAG
        
        This is ideal for:
        - Metro maps, floor plans, diagrams
        - Infographics with text labels
        - Scanned documents as images
        - Photos with visible text
        
        Args:
            blob_path: Path where image is stored in blob
            content: Image content as bytes
            filename: Original filename
            export_to_graphrag: If True, also export for GraphRAG indexing
            auto_index_graphrag: If provided, overrides settings.graphrag_auto_index
            
        Returns:
            Processing result with counts
        """
        self._auto_index_graphrag_override = auto_index_graphrag
        
        logger.info(f"Processing image with OCR + GPT-4V: {filename}")
        
        doc_id = self._sanitize_doc_id(filename)
        
        # 1. Run OCR with Document Intelligence (prebuilt-read)
        logger.info("Step 1: Running OCR with Document Intelligence...")
        ocr_text = await self._extract_ocr_from_image(content, filename)
        logger.info(f"   ✅ Extracted {len(ocr_text)} characters via OCR")
        
        # 2. Generate description with GPT-4V (Pass 1: comprehensive description)
        logger.info("Step 2a: Generating description with GPT-4V Vision...")
        vision_description = await self._generate_image_description(content, filename, ocr_text)
        logger.info(f"   ✅ Generated description: {vision_description[:100]}...")
        
        # 2b. Generate entity-relationship prose (Pass 2: structured for GraphRAG)
        logger.info("Step 2b: Generating entity-relationship prose with GPT-4V...")
        entity_prose = await self._generate_entity_relationship_prose(content, filename, vision_description)
        logger.info(f"   ✅ Generated entity prose: {len(entity_prose)} chars")
        
        # 3. Upload image to Blob Storage
        logger.info("Step 3: Uploading image to Blob Storage...")
        figure_id = f"image_000"  # Single image = single figure
        image_blob_path = await self.blob_service.upload_figure(content, doc_id, figure_id)
        # Note: store only the blob path, not the SAS URL - SAS will be generated at query time
        logger.info(f"   ✅ Uploaded to: {image_blob_path}")
        
        # 4. Create a single figure chunk with combined content
        logger.info("Step 4: Creating figure chunk...")
        
        # Combine content with MOST VALUABLE FIRST for embedding.
        # Embedding models truncate at ~8K tokens — put entity prose and
        # AI description before raw OCR so truncation cuts OCR (least valuable).
        content_parts = [f"Image: {filename}"]
        
        if entity_prose:
            content_parts.append(f"\nEntity-Relationship Analysis:\n{entity_prose}")
        
        content_parts.append(f"\nAI Visual Description:\n{vision_description}")
        
        if ocr_text:
            content_parts.append(f"\nOCR Extracted Text:\n{ocr_text}")
        else:
            content_parts.append("\nOCR Extracted Text:\n(No text detected)")
        
        combined_content = "\n".join(content_parts)
        
        chunk = {
            "id": f"{doc_id}_image_000",
            "content": combined_content,
            "content_type": "figure",
            "source_document": filename,
            "source_document_blob_path": blob_path,
            "page_numbers": [1],
            "section_header": f"Image: {filename}",
            "doc_id": doc_id,
            "image_blob_path": image_blob_path,  # Store blob path, NOT the full URL
            "figure_caption": vision_description[:500] if len(vision_description) > 500 else vision_description,
            # Store OCR and description separately for future use
            "ocr_text": ocr_text,
            "vision_description": vision_description
        }
        
        chunks = [chunk]
        logger.info(f"   ✅ Created 1 figure chunk")
        
        # 5. Generate embedding and index to Azure AI Search
        logger.info("Step 5: Generating embedding and indexing to Azure AI Search...")
        await self.search_service.index_chunks(chunks)
        logger.info(f"   ✅ Indexed 1 chunk to Azure AI Search")
        
        result = {
            "doc_id": doc_id,
            "filename": filename,
            "page_count": 1,
            "chunks_created": 1,
            "text_chunks": 0,
            "table_chunks": 0,
            "figure_chunks": 1,
            "figures_processed": 1,
            "figures_extracted": 1,
            "ocr_characters": len(ocr_text),
            "processing_mode": "image_ocr_gpt4v"
        }
        
        # 6. Export for GraphRAG (DUAL-INDEX)
        if export_to_graphrag and self.settings.graphrag_enabled:
            logger.info("Step 6: Exporting for GraphRAG...")
            try:
                graphrag_result = await self._export_to_graphrag(chunks, filename)
                result["graphrag_exported"] = True
                result["graphrag_path"] = graphrag_result.get("path", "")
                logger.info(f"   ✅ Exported to GraphRAG: {result['graphrag_path']}")
            except Exception as e:
                logger.warning(f"   ⚠️ GraphRAG export failed: {e}")
                result["graphrag_exported"] = False
                result["graphrag_error"] = str(e)
        
        logger.info(f"✅ Image processing complete: {result}")
        return result
    
    async def _extract_ocr_from_image(self, content: bytes, filename: str) -> str:
        """
        Extract text from image using Document Intelligence OCR (prebuilt-read model).
        
        Args:
            content: Image bytes
            filename: Filename for content type detection
            
        Returns:
            Extracted text as string
        """
        try:
            # Determine content type from filename
            ext = filename.lower().split('.')[-1] if '.' in filename else 'png'
            content_type_map = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "bmp": "image/bmp",
                "tiff": "image/tiff",
                "tif": "image/tiff",
                "heif": "image/heif",
            }
            content_type = content_type_map.get(ext, "image/png")
            
            logger.info(f"Running DI OCR on image ({content_type})...")
            
            # Use prebuilt-read model for OCR
            poller = self.di_client.begin_analyze_document(
                model_id="prebuilt-read",
                body=content,
                content_type=content_type
            )
            
            result = poller.result()
            
            # Extract all text content
            text_parts = []
            for page in result.pages:
                for line in page.lines:
                    text_parts.append(line.content)
            
            extracted_text = "\n".join(text_parts)
            logger.info(f"OCR extracted {len(text_parts)} lines, {len(extracted_text)} characters")
            
            return extracted_text
            
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return ""
    
    async def _generate_image_description(
        self, 
        content: bytes, 
        filename: str, 
        ocr_text: str
    ) -> str:
        """
        Generate a rich description of the image using GPT-4V Vision.
        
        Args:
            content: Image bytes
            filename: Filename for context
            ocr_text: OCR-extracted text to help guide description
            
        Returns:
            AI-generated description
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available for image description")
            return f"Image file: {filename}"
        
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(content).decode('utf-8')
            
            # Determine MIME type
            ext = filename.lower().split('.')[-1] if '.' in filename else 'png'
            mime_map = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg", 
                "png": "image/png",
                "bmp": "image/bmp",
                "tiff": "image/tiff",
                "tif": "image/tiff",
            }
            mime_type = mime_map.get(ext, "image/png")
            
            # Build comprehensive prompt
            prompt = f"""Analyze this image in detail for search indexing and retrieval.

Filename: {filename}

{"OCR detected the following text in the image:" if ocr_text else "No text was detected by OCR."}
{ocr_text[:2000] if ocr_text else ""}

Provide a comprehensive description including:
1. **Type of image**: Map, diagram, chart, photo, schematic, infographic, etc.
2. **Main subject**: What is this image primarily about?
3. **All visible elements**: List all labeled items, stations, routes, components, etc.
4. **Text and numbers**: Confirm or expand on the OCR text - note any text that OCR might have missed
5. **Relationships**: How are elements connected? What routes/paths exist?
6. **Colors and symbols**: What do different colors or symbols represent?
7. **Scale/dimensions**: If present, note any scale indicators or measurements

Write your response in the SAME LANGUAGE as the text in the image.
If the image contains Hebrew text, respond in Hebrew.
Be thorough - this description will be used for semantic search."""

            response = self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                    "detail": "high"  # Use high detail for maps/diagrams
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096  # Large budget for complex images (maps, schematics, diagrams)
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"Generated image description ({len(description)} chars)")
            return description
            
        except Exception as e:
            logger.warning(f"Failed to generate image description: {e}")
            return f"Image file: {filename}. OCR text: {ocr_text[:500]}" if ocr_text else f"Image file: {filename}"

    async def _generate_entity_relationship_prose(
        self,
        content: bytes,
        filename: str,
        description: str
    ) -> str:
        """
        Generate entity-relationship prose from an image using GPT-4V.
        
        This is a SECOND vision pass specifically designed to produce natural-language
        sentences that GraphRAG's entity extractor can parse. The output format is
        explicit: "Entity A is connected to Entity B", "Component X feeds into Component Y".
        
        This is domain-agnostic — works for transit maps, electronic schematics,
        medical diagrams, org charts, mechanical drawings, etc.
        
        Args:
            content: Image bytes
            filename: Filename for context
            description: The description from Pass 1 (provides context)
            
        Returns:
            Prose text with explicit entity-relationship sentences
        """
        if not self.openai_client:
            return ""
        
        try:
            image_b64 = base64.b64encode(content).decode('utf-8')
            ext = filename.lower().split('.')[-1] if '.' in filename else 'png'
            mime_map = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "bmp": "image/bmp",
                "tiff": "image/tiff", "tif": "image/tiff",
            }
            mime_type = mime_map.get(ext, "image/png")
            
            prompt = f"""You previously described this image as:
---
{description[:2000]}
---

Now, extract ALL entities and relationships visible in this image.
Write in COMPLETE SENTENCES using the pattern:
"[Entity A] is connected to / leads to / contains / feeds into [Entity B]."

Rules:
1. List EVERY distinct entity you can identify (names, labels, nodes, components, stations, items).
2. For EACH pair of entities that have a visible connection (line, arrow, path, adjacency, containment), write one sentence describing that relationship.
3. If entities are grouped (by color, region, box, branch), state the grouping: "[Entity X] belongs to [Group Y]."
4. If there is a sequence or ordering, state it: "[A] comes before [B]" or "[A] is followed by [B]."
5. Write in the SAME LANGUAGE as the text in the image.
6. Do NOT summarize — be exhaustive. List every entity and every connection.
7. Use bullet points (•) for listing entities and relationships. Do NOT use numbered lists
   (1, 2, 3...) because those numbers could be confused with actual identifiers (station
   numbers, component IDs, etc.) that appear in the image. Only use numbers that are
   actually visible in the image itself.
8. Use the EXACT names/labels visible in the image. If the image shows an ID or number
   next to a name (e.g., "Station 37 - Yosef Burg"), include it as-is. Do NOT assign
   your own sequential numbers to entities.

Start with a section listing all entities, then list all relationships."""

            response = self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            
            prose = response.choices[0].message.content.strip()
            logger.info(f"Generated entity-relationship prose ({len(prose)} chars)")
            return prose
            
        except Exception as e:
            logger.warning(f"Failed to generate entity-relationship prose: {e}")
            return ""

    async def _export_to_graphrag(self, chunks: List[Dict[str, Any]], filename: str) -> Dict[str, Any]:
        """
        Export enriched chunks for GraphRAG indexing.
        
        This enables the dual-index architecture where the same document
        content feeds both Azure AI Search and GraphRAG knowledge graph.
        
        NOTE: GraphRAG indexing is NOT run automatically because:
        1. It takes 30-60+ minutes for large documents (uses many LLM calls)
        2. It's expensive (entity extraction, community detection, summarization)
        3. Running it synchronously would timeout the upload request
        
        Users should trigger indexing manually via:
        - POST /api/graphrag/index endpoint
        - Or enable graphrag_auto_index in settings (runs in background)
        """
        from services.graphrag_exporter import GraphRAGExporter
        import asyncio
        
        graphrag_root = self.settings.graphrag_index_path or "./graphrag-index"
        exporter = GraphRAGExporter(graphrag_root)
        
        # Export chunks to text file
        output_path = exporter.export_chunks_for_graphrag(chunks, filename)
        
        # Optionally create/update GraphRAG config
        if not (exporter.graphrag_root / "settings.yaml").exists():
            exporter.create_graphrag_config(
                azure_openai_endpoint=self.settings.azure_openai_endpoint,
                azure_openai_api_key=self.settings.azure_openai_api_key,
                chat_model=self.settings.azure_openai_deployment,
                embedding_model=self.settings.azure_openai_embedding_deployment
            )
        
        result = {
            "path": str(output_path),
            "graphrag_root": graphrag_root,
            "index_status": "pending",
            "message": "Document exported for GraphRAG. Index needs to be built before GraphRAG queries will work."
        }
        
        # Check if auto-indexing should run:
        # 1. Use override if provided (from upload request)
        # 2. Otherwise use settings default
        should_auto_index = getattr(self, '_auto_index_graphrag_override', None)
        if should_auto_index is None:
            should_auto_index = getattr(self.settings, 'graphrag_auto_index', True)
        
        if should_auto_index:
            logger.info("GraphRAG auto-indexing enabled - starting background indexing...")
            result["index_status"] = "started"
            result["message"] = "GraphRAG indexing started in background. This may take 30-60 minutes."
            
            # Use the non-blocking background indexer (Popen, no timeout)
            # instead of run_graphrag_indexing() which blocks with a 600s timeout
            bg_result = exporter.start_graphrag_indexing_background()
            if bg_result.get("success"):
                logger.info(f"✅ GraphRAG background indexing launched (PID: {bg_result.get('pid', 'unknown')})")
            else:
                logger.warning(f"⚠️ GraphRAG background indexing failed to start: {bg_result.get('error', 'unknown')}")
        else:
            logger.info("GraphRAG auto-indexing disabled. Run POST /api/graphrag/index to build the index.")
        
        return result
    
    async def _save_di_result(self, di_result: Dict[str, Any], filename: str):
        """Save DI result for debugging."""
        import json
        from pathlib import Path
        
        output_dir = Path(__file__).parent.parent / "output" / "di_results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = Path(filename).stem
        output_path = output_dir / f"{base_name}_di_result.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(di_result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"   Saved DI result to: {output_path}")
    
    async def _analyze_with_di(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document with Document Intelligence.
        
        Uses prebuilt-layout model to extract:
        - Text with reading order
        - Tables with cell structure
        - Figures with bounding boxes
        """
        # Validate file format: detect legacy Office formats disguised with modern extensions.
        # OLE2 Compound Document (magic: D0CF11E0) = legacy .doc/.xls/.ppt (Word/Excel/PPT 97-2003).
        # DI only supports modern Office Open XML formats (.docx/.xlsx/.pptx = ZIP-based, magic: 504B).
        ext = filename.lower().rsplit(".", 1)[-1]
        if content[:4] == b'\xd0\xcf\x11\xe0' and ext in ("docx", "xlsx", "pptx"):
            legacy_ext = {"docx": ".doc", "xlsx": ".xls", "pptx": ".ppt"}[ext]
            raise ValueError(
                f"'{filename}' is a legacy Office file ({legacy_ext} format) renamed to .{ext}. "
                f"Azure Document Intelligence only supports modern Office Open XML formats. "
                f"Please re-save the file as .{ext} using File → Save As in Word/Excel/PowerPoint."
            )
        
        # Analyze document - using prebuilt-layout which includes figures by default
        # Use AnalyzeDocumentRequest with bytes_source so the SDK sends the request
        # as JSON with base64 encoding. Passing raw bytes causes the SDK to force
        # content_type="application/octet-stream", which fails for Office formats
        # (.docx, .xlsx, .pptx) because DI cannot detect their type from raw bytes.
        logger.info(f"Analyzing document with DI: {filename}")
        poller = self.di_client.begin_analyze_document(
            "prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=content),
        )
        
        result = poller.result()
        
        # Convert to dict for easier processing
        return {
            "content": result.content,
            "pages": [
                {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "unit": page.unit
                }
                for page in (result.pages or [])
            ],
            "paragraphs": [
                {
                    "content": para.content,
                    "role": para.role,
                    "bounding_regions": [
                        {
                            "page_number": br.page_number,
                            "polygon": br.polygon
                        }
                        for br in (para.bounding_regions or [])
                    ]
                }
                for para in (result.paragraphs or [])
            ],
            "tables": [
                {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [
                        {
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                            "kind": cell.kind
                        }
                        for cell in (table.cells or [])
                    ],
                    "bounding_regions": [
                        {
                            "page_number": br.page_number,
                            "polygon": br.polygon
                        }
                        for br in (table.bounding_regions or [])
                    ]
                }
                for table in (result.tables or [])
            ],
            "figures": [
                {
                    "id": fig.id,
                    "caption": fig.caption.content if fig.caption else None,
                    "bounding_regions": [
                        {
                            "page_number": br.page_number,
                            "polygon": br.polygon
                        }
                        for br in (fig.bounding_regions or [])
                    ]
                }
                for fig in (result.figures or [])
            ],
            "page_count": len(result.pages) if result.pages else 0
        }
    
    async def _extract_figures(
        self,
        content: bytes,
        di_result: Dict[str, Any],
        doc_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Extract figures using bounding boxes from DI + GPT-4V descriptions.
        
        For PDFs, converts pages to images, crops figures, and generates
        semantic descriptions using GPT-4 Vision WITH SECTION CONTEXT.
        
        Uses PARALLEL processing with rate limiting for speed.
        """
        import asyncio
        
        figures = []
        ext = filename.lower().split(".")[-1]
        
        # Build page context map for better descriptions
        page_context = self._build_page_context(di_result)
        
        # Build page-to-section map EARLY so we can pass section context to GPT-4V
        page_to_section = self._build_page_section_map(di_result)
        logger.info(f"Built section map: {len(set(page_to_section.values()))} unique sections for figure extraction")
        
        if ext != "pdf":
            # For Office files, figure extraction is more complex
            for i, fig in enumerate(di_result.get("figures", [])):
                page_nums = [br["page_number"] for br in fig.get("bounding_regions", [])]
                context = page_context.get(page_nums[0] if page_nums else 1, "")
                section = page_to_section.get(page_nums[0] if page_nums else 1, "")
                figures.append({
                    "id": f"fig_{i:03d}",
                    "caption": fig.get("caption", ""),
                    "description": fig.get("caption", "") or context[:200],
                    "page_numbers": page_nums,
                    "blob_path": None,
                    "section": section
                })
            return figures
        
        # For PDFs, use pdf2image to extract figures WITH PARALLEL GPT-4V CALLS
        try:
            from pdf2image import convert_from_bytes
            
            # Convert PDF pages to images
            logger.info(f"Converting PDF to images for figure extraction...")
            page_images = convert_from_bytes(content, dpi=150)
            
            total_figures = len(di_result.get("figures", []))
            logger.info(f"Extracting {total_figures} figures with PARALLEL GPT-4V processing (max 5 concurrent)...")
            
            # Rate limiter: max 5 concurrent GPT-4V calls to avoid rate limits
            semaphore = asyncio.Semaphore(5)
            
            # Prepare all figure data first (cropping, uploading)
            figure_tasks = []
            
            for i, fig in enumerate(di_result.get("figures", [])):
                for br in fig.get("bounding_regions", []):
                    page_num = br["page_number"]
                    polygon = br.get("polygon", [])
                    
                    if page_num <= len(page_images) and len(polygon) >= 4:
                        page_img = page_images[page_num - 1]
                        
                        # Get bounding box from polygon
                        xs = [polygon[j] for j in range(0, len(polygon), 2)]
                        ys = [polygon[j] for j in range(1, len(polygon), 2)]
                        
                        # Get page dimensions from DI
                        page_info = di_result["pages"][page_num - 1]
                        page_width = page_info["width"]
                        page_height = page_info["height"]
                        
                        # Scale coordinates to image size
                        img_width, img_height = page_img.size
                        scale_x = img_width / page_width
                        scale_y = img_height / page_height
                        
                        left = int(min(xs) * scale_x)
                        top = int(min(ys) * scale_y)
                        right = int(max(xs) * scale_x)
                        bottom = int(max(ys) * scale_y)
                        
                        # Add padding to avoid cutting off labels (5% of figure size)
                        pad_x = int((right - left) * 0.05)
                        pad_y = int((bottom - top) * 0.05)
                        left = max(0, left - pad_x)
                        top = max(0, top - pad_y)
                        right = min(img_width, right + pad_x)
                        bottom = min(img_height, bottom + pad_y)
                        
                        # Crop figure
                        cropped = page_img.crop((left, top, right, bottom))
                        
                        # Save to bytes
                        img_buffer = io.BytesIO()
                        cropped.save(img_buffer, format="PNG")
                        img_bytes = img_buffer.getvalue()
                        
                        # Get context for this figure
                        section = page_to_section.get(page_num, "")
                        caption = fig.get("caption", "")
                        context = page_context.get(page_num, "")
                        
                        # Create task for parallel processing
                        figure_tasks.append({
                            "index": i,
                            "img_bytes": img_bytes,
                            "caption": caption,
                            "section": section,
                            "context": context,
                            "page_num": page_num,
                            "doc_id": doc_id,
                            "bounding_box": {"left": left, "top": top, "right": right, "bottom": bottom}
                        })
                        
                        break  # Only process first bounding region
            
            # Process all figures in parallel with rate limiting
            async def process_single_figure(task_data):
                async with semaphore:
                    figure_id = f"fig_{task_data['index']:03d}"
                    
                    # Upload to blob
                    blob_path_fig = await self.blob_service.upload_figure(
                        task_data["img_bytes"], task_data["doc_id"], figure_id
                    )
                    
                    # Generate description using GPT-4V WITH SECTION CONTEXT
                    description = await self._generate_figure_description(
                        task_data["img_bytes"],
                        caption=task_data["caption"],
                        page_context=task_data["context"],
                        section_context=task_data["section"]
                    )
                    
                    return {
                        "id": figure_id,
                        "caption": task_data["caption"],
                        "description": description,
                        "page_numbers": [task_data["page_num"]],
                        "blob_path": blob_path_fig,
                        "section": task_data["section"],
                        "bounding_box": task_data["bounding_box"]
                    }
            
            # Run all tasks in parallel
            logger.info(f"Starting parallel GPT-4V processing for {len(figure_tasks)} figures...")
            results = await asyncio.gather(*[process_single_figure(t) for t in figure_tasks])
            figures = list(results)
            
            logger.info(f"Parallel processing complete: {len(figures)} figures processed")
                        
        except ImportError:
            logger.warning("pdf2image not installed; figures indexed without images")
            for i, fig in enumerate(di_result.get("figures", [])):
                page_nums = [br["page_number"] for br in fig.get("bounding_regions", [])]
                figures.append({
                    "id": f"fig_{i:03d}",
                    "caption": fig.get("caption", ""),
                    "description": fig.get("caption", ""),
                    "page_numbers": page_nums,
                    "blob_path": None
                })
        except Exception as e:
            logger.warning(f"Figure extraction error: {e}")
            for i, fig in enumerate(di_result.get("figures", [])):
                page_nums = [br["page_number"] for br in fig.get("bounding_regions", [])]
                figures.append({
                    "id": f"fig_{i:03d}",
                    "caption": fig.get("caption", ""),
                    "description": fig.get("caption", ""),
                    "page_numbers": page_nums,
                    "blob_path": None
                })
        
        logger.info(f"Figure extraction complete: {len(figures)} figures processed")
        return figures
    
    def _build_page_context(self, di_result: Dict[str, Any]) -> Dict[int, str]:
        """
        Build a map of page number -> text context for better figure descriptions.
        """
        page_context = {}
        
        for para in di_result.get("paragraphs", []):
            content = para.get("content", "").strip()
            if not content:
                continue
                
            for br in para.get("bounding_regions", []):
                page_num = br["page_number"]
                if page_num not in page_context:
                    page_context[page_num] = ""
                page_context[page_num] += content + " "
        
        # Trim to reasonable length
        for page_num in page_context:
            page_context[page_num] = page_context[page_num][:1000]
        
        return page_context
    
    def _build_page_section_map(self, di_result: Dict[str, Any]) -> Dict[int, str]:
        """
        Build a map of page number → section header.
        
        This allows us to assign section context to figures and tables
        based on what section their page belongs to.
        
        The logic: When we encounter a sectionHeading, all following pages
        belong to that section until we hit the next sectionHeading.
        """
        page_to_section = {}
        current_section = "Introduction"
        last_page_seen = 0
        
        # First pass: find section headings and their starting pages
        section_starts = []  # List of (page_number, section_name)
        
        for para in di_result.get("paragraphs", []):
            role = para.get("role", "")
            content = para.get("content", "").strip()
            
            if not content:
                continue
            
            # Get page number for this paragraph
            for br in para.get("bounding_regions", []):
                page_num = br["page_number"]
                last_page_seen = max(last_page_seen, page_num)
                
                # If this is a section heading, record it
                if role in ["sectionHeading", "title"]:
                    section_starts.append((page_num, content))
                    break
        
        # Sort by page number
        section_starts.sort(key=lambda x: x[0])
        
        # Second pass: assign sections to all pages
        total_pages = di_result.get("page_count", last_page_seen)
        
        for page_num in range(1, total_pages + 1):
            # Find the most recent section that started on or before this page
            current_section = "Introduction"
            for start_page, section_name in section_starts:
                if start_page <= page_num:
                    current_section = section_name
                else:
                    break
            page_to_section[page_num] = current_section
        
        return page_to_section
    
    async def _create_chunks(
        self,
        di_result: Dict[str, Any],
        doc_id: str,
        filename: str,
        blob_path: str,
        figures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from DI result.
        
        Chunk types:
        - text: Paragraphs grouped by section
        - table: Each table as atomic chunk with section context
        - figure: Each figure with description + FULL DOCUMENT CONTEXT
        
        IMPORTANT: Figure chunks include:
        - Document name (for "figures in document X" queries)
        - Section hierarchy (for "safety diagrams" queries)
        - Page number (for "figure on page 5" queries)
        - Surrounding text (for semantic understanding)
        - GPT-4V description (for visual content)
        """
        chunks = []
        chunk_id = 0
        
        # Maximum content size for embedding (chars, ~8000 tokens * 3 chars/token)
        MAX_CHUNK_CHARS = 20000
        
        # Build context maps
        page_to_section = self._build_page_section_map(di_result)
        page_context = self._build_page_context(di_result)
        
        # Build figure-to-nearby-text map for richer context
        figure_nearby_text = self._get_nearby_text_for_figures(di_result, figures)
        
        logger.info(f"Built context maps: {len(set(page_to_section.values()))} sections, {len(page_context)} pages with text")
        
        # Helper to split large content into smaller chunks
        def split_large_content(content: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
            """Split large content into smaller pieces at logical boundaries."""
            if len(content) <= max_chars:
                return [content]
            
            parts = []
            remaining = content
            while remaining:
                if len(remaining) <= max_chars:
                    parts.append(remaining)
                    break
                
                # Try to split at a paragraph or line boundary
                chunk = remaining[:max_chars]
                
                # Look for last double newline (paragraph break)
                split_at = chunk.rfind('\n\n')
                if split_at < max_chars * 0.5:
                    # Look for last single newline
                    split_at = chunk.rfind('\n')
                if split_at < max_chars * 0.5:
                    # Just split at max_chars
                    split_at = max_chars
                
                parts.append(remaining[:split_at].strip())
                remaining = remaining[split_at:].strip()
            
            return parts
        
        # 1. Text chunks from paragraphs
        current_section = "Introduction"
        current_content = []
        current_pages = set()
        
        for para in di_result.get("paragraphs", []):
            role = para.get("role", "")
            content = para.get("content", "").strip()
            
            if not content:
                continue
            
            # Extract page numbers
            for br in para.get("bounding_regions", []):
                current_pages.add(br["page_number"])
            
            # Check for section header
            if role in ["sectionHeading", "title"]:
                # Save previous section
                if current_content:
                    chunks.append({
                        "id": f"{doc_id}_text_{chunk_id:04d}",
                        "content": "\n\n".join(current_content),
                        "content_type": "text",
                        "source_document": filename,
                        "source_document_blob_path": blob_path,
                        "page_numbers": sorted(list(current_pages)),
                        "section_header": current_section,
                        "doc_id": doc_id
                    })
                    chunk_id += 1
                
                # Start new section
                current_section = content
                current_content = []
                current_pages = set()
            else:
                current_content.append(content)
        
        # Don't forget last section
        if current_content:
            section_content = "\n\n".join(current_content)
            # Split if too large
            content_parts_split = split_large_content(section_content)
            for part_idx, part in enumerate(content_parts_split):
                part_suffix = f"_p{part_idx}" if len(content_parts_split) > 1 else ""
                chunks.append({
                    "id": f"{doc_id}_text_{chunk_id:04d}{part_suffix}",
                    "content": part,
                    "content_type": "text",
                    "source_document": filename,
                    "source_document_blob_path": blob_path,
                    "page_numbers": sorted(list(current_pages)),
                    "section_header": current_section,
                    "doc_id": doc_id
                })
            chunk_id += 1
        
        # 2. Table chunks - with section context
        for i, table in enumerate(di_result.get("tables", [])):
            table_md = self._table_to_markdown(table)
            
            page_nums = [
                br["page_number"] 
                for br in table.get("bounding_regions", [])
            ]
            
            table_section = page_to_section.get(page_nums[0], "") if page_nums else ""
            
            # Build rich content for embedding
            content_parts = [
                f"Document: {filename}",
                f"Section: {table_section}" if table_section else "",
                f"Page: {page_nums[0]}" if page_nums else "",
                "",
                "Table Content:",
                table_md
            ]
            rich_content = "\n".join(p for p in content_parts if p)
            
            # Split large tables into multiple chunks
            if len(rich_content) > MAX_CHUNK_CHARS:
                logger.warning(f"Table {i} is very large ({len(rich_content)} chars), splitting into multiple chunks")
                table_parts = split_large_content(rich_content)
                for part_idx, part in enumerate(table_parts):
                    chunks.append({
                        "id": f"{doc_id}_table_{i:04d}_p{part_idx}",
                        "content": part,
                        "content_type": "table",
                        "source_document": filename,
                        "source_document_blob_path": blob_path,
                        "page_numbers": page_nums,
                        "section_header": table_section,
                        "doc_id": doc_id,
                        "table_html": self._table_to_html(table) if part_idx == 0 else "",
                        "table_markdown": table_md if part_idx == 0 else part
                    })
            else:
                chunks.append({
                    "id": f"{doc_id}_table_{i:04d}",
                    "content": rich_content,
                    "content_type": "table",
                    "source_document": filename,
                    "source_document_blob_path": blob_path,
                    "page_numbers": page_nums,
                    "section_header": table_section,
                    "doc_id": doc_id,
                    "table_html": self._table_to_html(table),
                    "table_markdown": table_md
                })
        
        # 3. Figure chunks - with FULL DOCUMENT CONTEXT
        for fig in figures:
            fig_id = fig.get("id", "unknown")
            fig_pages = fig.get("page_numbers", [])
            fig_section = page_to_section.get(fig_pages[0], "") if fig_pages else ""
            
            # Get GPT-4V description
            description = fig.get("description", "")
            caption = fig.get("caption", "")
            
            # Get surrounding text for this figure
            nearby_text = figure_nearby_text.get(fig_id, "")
            
            # Build RICH content for embedding that includes ALL context
            # This is what gets embedded and searched!
            content_parts = [
                f"Document: {filename}",
                f"Section: {fig_section}" if fig_section else "",
                f"Page: {fig_pages[0]}" if fig_pages else "",
            ]
            
            # Add surrounding context
            if nearby_text:
                content_parts.append("")
                content_parts.append("Surrounding Context:")
                content_parts.append(nearby_text[:500])  # Limit to 500 chars
            
            # Add figure description
            content_parts.append("")
            content_parts.append("Figure Description:")
            if description:
                content_parts.append(description)
            elif caption:
                content_parts.append(f"Figure showing: {caption}")
            else:
                content_parts.append("Figure (no description available)")
            
            full_content = "\n".join(p for p in content_parts if p is not None)
            
            chunks.append({
                "id": f"{doc_id}_{fig_id}",
                "content": full_content,
                "content_type": "figure",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": fig_pages,
                "section_header": fig_section,
                "doc_id": doc_id,
                "image_blob_path": fig.get("blob_path"),
                "figure_caption": caption,
                "figure_description": description,
                "surrounding_text": nearby_text[:500] if nearby_text else ""
            })
        
        logger.info(f"Created {len(chunks)} chunks (text: {chunk_id}, tables: {len(di_result.get('tables', []))}, figures: {len(figures)})")
        return chunks
    
    def _get_nearby_text_for_figures(
        self, 
        di_result: Dict[str, Any], 
        figures: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Get text paragraphs that are near each figure (same page, before/after).
        
        This provides context for what the figure is about based on surrounding text.
        """
        figure_nearby = {}
        
        # Build list of paragraphs per page
        page_paragraphs = {}
        for para in di_result.get("paragraphs", []):
            content = para.get("content", "").strip()
            if not content:
                continue
            for br in para.get("bounding_regions", []):
                page_num = br["page_number"]
                if page_num not in page_paragraphs:
                    page_paragraphs[page_num] = []
                page_paragraphs[page_num].append(content)
        
        # For each figure, get text from same page
        for fig in figures:
            fig_id = fig.get("id", "")
            fig_pages = fig.get("page_numbers", [])
            
            nearby_text = []
            for page_num in fig_pages:
                if page_num in page_paragraphs:
                    # Get paragraphs from this page (limit to avoid too much text)
                    page_text = page_paragraphs[page_num][:5]  # First 5 paragraphs
                    nearby_text.extend(page_text)
            
            figure_nearby[fig_id] = " ".join(nearby_text)
        
        return figure_nearby
    
    def _table_to_markdown(self, table: Dict[str, Any]) -> str:
        """Convert table to markdown format."""
        rows = [[None] * table["column_count"] for _ in range(table["row_count"])]
        
        for cell in table.get("cells", []):
            r, c = cell["row_index"], cell["column_index"]
            if r < len(rows) and c < len(rows[0]):
                rows[r][c] = cell["content"]
        
        # Build markdown
        lines = []
        for i, row in enumerate(rows):
            line = "| " + " | ".join(str(c or "") for c in row) + " |"
            lines.append(line)
            if i == 0:
                # Header separator
                lines.append("| " + " | ".join(["---"] * len(row)) + " |")
        
        return "\n".join(lines)
    
    def _table_to_html(self, table: Dict[str, Any]) -> str:
        """Convert table to HTML format."""
        rows = [[None] * table["column_count"] for _ in range(table["row_count"])]
        
        for cell in table.get("cells", []):
            r, c = cell["row_index"], cell["column_index"]
            if r < len(rows) and c < len(rows[0]):
                rows[r][c] = cell["content"]
        
        html = ["<table>"]
        for i, row in enumerate(rows):
            html.append("<tr>")
            tag = "th" if i == 0 else "td"
            for cell in row:
                html.append(f"<{tag}>{cell or ''}</{tag}>")
            html.append("</tr>")
        html.append("</table>")
        
        return "".join(html)
