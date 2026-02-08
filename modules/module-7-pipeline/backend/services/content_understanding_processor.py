"""
Document Processor Service using Content Understanding.

This processor uses Azure Content Understanding instead of Document Intelligence.
CU provides:
- Markdown output for easy chunking
- Elements inside figures (text in figures)
- AI-generated figure descriptions (with enableFigureDescription)
- AI-generated field extraction (summary, topics)
"""

import io
import logging
import base64
import re
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from azure.ai.contentunderstanding import ContentUnderstandingClient as OfficialCUClient
    from azure.core.credentials import AzureKeyCredential
    CU_SDK_AVAILABLE = True
except ImportError:
    CU_SDK_AVAILABLE = False

from config.settings import get_settings
from services.blob_service import BlobService
from services.search_service import SearchService
from services.content_understanding_client import AzureContentUnderstandingClient

logger = logging.getLogger(__name__)

# Use prebuilt-layout analyzer - returns figures/tables with bounding boxes
# (prebuilt-documentSearch only returns text for search, no figures!)
DEFAULT_ANALYZER_ID = "prebuilt-layout"


class ContentUnderstandingProcessor:
    """
    Document processing using Azure Content Understanding.
    
    Flow:
    1. CU extracts layout, tables, figures with markdown output
    2. Figures are cropped from PDF and stored in blob
    3. Markdown content is chunked by headers
    4. Chunks are indexed in Azure AI Search
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_service = BlobService()
        self.search_service = SearchService()
        self._cu_client = None
        self._openai_client = None
        self._analyzer_id = DEFAULT_ANALYZER_ID
        
        logger.info(f"ContentUnderstandingProcessor initialized (Pillow: {PILLOW_AVAILABLE}, OpenAI: {OPENAI_AVAILABLE})")
    
    @property
    def cu_client(self) -> AzureContentUnderstandingClient:
        """Get Content Understanding client (custom REST client with :analyzeBinary support)."""
        if self._cu_client is None:
            # Get endpoint - CU uses .services.ai.azure.com
            endpoint = self.settings.azure_content_understanding_endpoint
            if not endpoint:
                endpoint = getattr(self.settings, 'azure_ai_services_endpoint', '')
            if not endpoint:
                endpoint = self.settings.azure_document_intelligence_endpoint
            
            key = self.settings.azure_content_understanding_key
            if not key:
                key = getattr(self.settings, 'azure_ai_services_key', '')
            if not key:
                key = self.settings.azure_document_intelligence_key
            
            api_version = self.settings.azure_content_understanding_api_version
            
            if not endpoint or not key:
                raise RuntimeError("Content Understanding endpoint and key must be configured.")
            
            # Use our custom REST client that uses :analyzeBinary endpoint correctly
            # The official SDK has issues with ContentEmpty errors
            self._cu_client = AzureContentUnderstandingClient(
                endpoint=endpoint,
                subscription_key=key,
                api_version=api_version,
            )
            logger.info(f"Created custom CU client for {endpoint} (api_version={api_version})")
        return self._cu_client
    
    @property
    def openai_client(self):
        """Get Azure OpenAI client for vision (fallback for figure descriptions)."""
        if not OPENAI_AVAILABLE:
            return None
        
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-10-21",
                azure_endpoint=self.settings.azure_openai_endpoint
            )
        return self._openai_client
    
    async def process_document(
        self,
        blob_path: str,
        content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process a document end-to-end using Content Understanding.
        
        Args:
            blob_path: Path where document is stored in blob
            content: Document content as bytes
            filename: Original filename
            
        Returns:
            Processing result with counts
        """
        # File size validation - Content Understanding has limits
        file_size_mb = len(content) / 1024 / 1024
        MAX_FILE_SIZE_MB = 50  # CU recommended limit
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"⚠️  Large file detected: {file_size_mb:.1f} MB (recommended limit: {MAX_FILE_SIZE_MB} MB)")
            logger.warning("Large files may time out or return ContentEmpty errors.")
        
        logger.info(f"Processing document: {filename} ({file_size_mb:.1f} MB)")
        
        # Extract document ID from blob path and sanitize for Azure AI Search key requirements
        # Keys can only contain letters, digits, underscore (_), dash (-), or equal sign (=)
        raw_id = blob_path.split("/")[1] if "/" in blob_path else blob_path
        doc_id = re.sub(r'[^a-zA-Z0-9_\-=]', '', raw_id.replace('.', '_').replace(' ', '_'))[:50]
        
        # Use prebuilt analyzer (no need to create custom)
        analyzer_id = self._analyzer_id
        
        # 1. Analyze with Content Understanding
        logger.info(f"Analyzing document with Content Understanding: {filename}")
        cu_result = await self._analyze_with_cu(content, filename, analyzer_id)
        
        # Save CU result locally for debugging/caching
        await self._save_cu_result(cu_result, filename, doc_id)
        
        # 2. Extract and store figures
        figures = await self._extract_figures(content, cu_result, doc_id, filename)
        
        # 3. Create chunks from CU result
        chunks = await self._create_chunks(cu_result, doc_id, filename, blob_path, figures)
        
        # 4. Generate embeddings and index chunks
        await self.search_service.index_chunks(chunks)
        
        return {
            "chunks_created": len(chunks),
            "figures_extracted": len(figures),
            "tables_found": len(cu_result.get("tables", [])),
            "pages": cu_result.get("page_count", 0),
            "processing_mode": "content_understanding"
        }
    
    async def _save_cu_result(
        self,
        cu_result: Dict[str, Any],
        filename: str,
        doc_id: str
    ) -> None:
        """
        Save Content Understanding result to local file for debugging/caching.
        
        Saved to: module-7-pipeline/output/cu_results/{filename}.json
        """
        import json
        
        # Create output directory
        output_dir = Path(__file__).parent.parent / "output" / "cu_results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        base_name = Path(filename).stem
        output_path = output_dir / f"{base_name}_cu_result.json"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(cu_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved CU result to: {output_path}")
            logger.info(f"   Markdown: {len(cu_result.get('markdown', ''))} chars")
            logger.info(f"   Pages: {cu_result.get('page_count', 0)}")
            logger.info(f"   Tables: {len(cu_result.get('tables', []))}")
            logger.info(f"   Figures: {len(cu_result.get('figures', []))}")
        except Exception as e:
            logger.warning(f"Failed to save CU result: {e}")
    
    def _load_cached_cu_result(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a cached CU result if it exists.
        
        Useful for development/demos to avoid re-processing.
        Set USE_CACHED_CU_RESULT=true in .env to enable.
        """
        import json
        
        # Check if caching is enabled
        use_cache = getattr(self.settings, 'use_cached_cu_result', False)
        if not use_cache:
            return None
        
        # Check for cached file
        output_dir = Path(__file__).parent.parent / "output" / "cu_results"
        base_name = Path(filename).stem
        cache_path = output_dir / f"{base_name}_cu_result.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info(f"📂 Loaded cached CU result from: {cache_path}")
                return cached
            except Exception as e:
                logger.warning(f"Failed to load cached CU result: {e}")
        
        return None

    async def _analyze_with_cu(
        self, 
        content: bytes, 
        filename: str,
        analyzer_id: str
    ) -> Dict[str, Any]:
        """
        Analyze document with Content Understanding using custom REST client.
        
        Uses :analyzeBinary endpoint which is the correct endpoint for binary uploads.
        The official SDK has issues with ContentEmpty errors.
        
        Returns normalized result dict compatible with our pipeline.
        """
        # Check for cached result first (useful for development)
        cached = self._load_cached_cu_result(filename)
        if cached:
            return cached
        
        # Determine content type
        ext = filename.lower().split(".")[-1]
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }
        
        content_type = content_type_map.get(ext, "application/pdf")
        
        # Analyze document using custom REST client with :analyzeBinary
        logger.info(f"Starting CU analysis with {analyzer_id} (using :analyzeBinary endpoint)...")
        logger.info(f"Document size: {len(content)} bytes, content_type: {content_type}")
        
        try:
            # Use custom client that properly uses :analyzeBinary endpoint
            response = self.cu_client.begin_analyze(
                analyzer_id=analyzer_id,
                file_content=content,
                content_type=content_type
            )
            
            # Poll for result
            logger.info("Waiting for CU analysis to complete (this may take several minutes)...")
            result_dict = self.cu_client.poll_result(
                response,
                timeout_seconds=1200,  # 20 minutes for large documents
                polling_interval_seconds=5,
            )
        except Exception as e:
            error_str = str(e)
            if "ContentEmpty" in error_str:
                logger.error(f"Content Understanding returned 'ContentEmpty' error.")
                logger.error("="*60)
                logger.error("⚠️  CONTENT UNDERSTANDING ERROR")
                logger.error("="*60)
                logger.error("")
                logger.error("The Azure AI Content Understanding service returned 'ContentEmpty'.")
                logger.error("This can happen if:")
                logger.error("  - The document is too large (try files under 20MB)")
                logger.error("  - The document format is not supported")
                logger.error("  - There's a temporary service issue")
                logger.error("")
                logger.error("DIAGNOSTIC INFO:")
                logger.error(f"  Endpoint: {self.cu_client._endpoint}")
                logger.error(f"  Analyzer: {analyzer_id}")
                logger.error(f"  Document size: {len(content)} bytes ({len(content) / 1024 / 1024:.1f} MB)")
                logger.error(f"  Content type: {content_type}")
                logger.error("")
            raise RuntimeError(f"Content Understanding analysis failed: {e}") from e
        
        logger.info(f"CU analysis complete. Result keys: {list(result_dict.keys())}")
        
        # Extract the inner 'result' object if present (poll_result returns {status, result, ...})
        if "result" in result_dict:
            inner_result = result_dict["result"]
            logger.info(f"Inner result keys: {list(inner_result.keys())}")
        else:
            inner_result = result_dict
        
        # Get contents (CU returns markdown in contents array)
        contents = inner_result.get("contents", [])
        
        # Build normalized result
        normalized = {
            "markdown": "",
            "pages": [],
            "paragraphs": [],
            "tables": [],
            "figures": [],
            "sections": [],
            "fields": {},
            "page_count": 0,
        }
        
        # Process each content block
        for content_block in contents:
            # Markdown output - this is the key CU advantage
            if "markdown" in content_block:
                normalized["markdown"] += content_block["markdown"] + "\n\n"
            
            # AI-generated fields (summary, topics, etc.)
            if "fields" in content_block:
                normalized["fields"].update(content_block["fields"])
            
            # Pages - CU puts them directly in content block
            if "pages" in content_block:
                for page in content_block["pages"]:
                    normalized["pages"].append({
                        "page_number": page.get("pageNumber", 1),
                        "width": page.get("width", 8.5),
                        "height": page.get("height", 11),
                        "unit": page.get("unit", "inch")
                    })
            
            # Paragraphs
            if "paragraphs" in content_block:
                for p in content_block["paragraphs"]:
                    normalized["paragraphs"].append({
                        "content": p.get("content", ""),
                        "role": p.get("role", ""),
                        "bounding_regions": [
                            {
                                "page_number": br.get("pageNumber", 1),
                                "polygon": br.get("polygon", [])
                            }
                            for br in p.get("boundingRegions", [])
                        ]
                    })
            
            # Sections
            if "sections" in content_block:
                for s in content_block["sections"]:
                    normalized["sections"].append({
                        "content": s.get("content", ""),
                        "elements": s.get("elements", [])
                    })
            
            # Tables
            if "tables" in content_block:
                for t in content_block["tables"]:
                    normalized["tables"].append({
                        "row_count": t.get("rowCount", 0),
                        "column_count": t.get("columnCount", 0),
                        "cells": [
                            {
                                "row_index": c.get("rowIndex", 0),
                                "column_index": c.get("columnIndex", 0),
                                "content": c.get("content", ""),
                                "kind": c.get("kind", "content")
                            }
                            for c in t.get("cells", [])
                        ],
                        "bounding_regions": [
                            {
                                "page_number": br.get("pageNumber", 1),
                                "polygon": br.get("polygon", [])
                            }
                            for br in t.get("boundingRegions", [])
                        ]
                    })
        
        # Calculate page count
        normalized["page_count"] = len(normalized["pages"]) or len(contents)
        
        # Fallback: Also check top-level analyzeResult structure (for DI compatibility)
        if "analyzeResult" in inner_result:
            ar = inner_result["analyzeResult"]
            
            if "pages" in ar:
                normalized["pages"] = [
                    {
                        "page_number": p.get("pageNumber", i+1),
                        "width": p.get("width", 8.5),
                        "height": p.get("height", 11),
                        "unit": p.get("unit", "inch")
                    }
                    for i, p in enumerate(ar["pages"])
                ]
            
            if "paragraphs" in ar:
                normalized["paragraphs"] = [
                    {
                        "content": p.get("content", ""),
                        "role": p.get("role", ""),
                        "bounding_regions": [
                            {
                                "page_number": br.get("pageNumber", 1),
                                "polygon": br.get("polygon", [])
                            }
                            for br in p.get("boundingRegions", [])
                        ]
                    }
                    for p in ar["paragraphs"]
                ]
            
            if "tables" in ar:
                normalized["tables"] = [
                    {
                        "row_count": t.get("rowCount", 0),
                        "column_count": t.get("columnCount", 0),
                        "cells": [
                            {
                                "row_index": c.get("rowIndex", 0),
                                "column_index": c.get("columnIndex", 0),
                                "content": c.get("content", ""),
                                "kind": c.get("kind", "content")
                            }
                            for c in t.get("cells", [])
                        ],
                        "bounding_regions": [
                            {
                                "page_number": br.get("pageNumber", 1),
                                "polygon": br.get("polygon", [])
                            }
                            for br in t.get("boundingRegions", [])
                        ]
                    }
                    for t in ar["tables"]
                ]
            
            if "figures" in ar:
                normalized["figures"] = [
                    {
                        "id": f.get("id", f"fig_{i}"),
                        "caption": f.get("caption", {}).get("content") if f.get("caption") else None,
                        "elements": f.get("elements", []),  # CU provides elements inside figures
                        "bounding_regions": [
                            {
                                "page_number": br.get("pageNumber", 1),
                                "polygon": br.get("polygon", [])
                            }
                            for br in f.get("boundingRegions", [])
                        ]
                    }
                    for i, f in enumerate(ar["figures"])
                ]
            
            if "sections" in ar:
                normalized["sections"] = ar["sections"]
        
        normalized["page_count"] = len(normalized["pages"])
        
        # CRITICAL: Content Understanding embeds figure references in markdown
        # as ![alt](figures/X.Y "description") but doesn't populate figures array.
        # Extract figures from markdown if figures array is empty.
        if not normalized["figures"] and normalized["markdown"]:
            markdown_figures = self._extract_figures_from_markdown(normalized["markdown"])
            if markdown_figures:
                normalized["figures"] = markdown_figures
                logger.info(f"📸 Extracted {len(markdown_figures)} figures from markdown")
        
        logger.info(f"CU analysis complete: {normalized['page_count']} pages, "
                   f"{len(normalized['paragraphs'])} paragraphs, "
                   f"{len(normalized['figures'])} figures, "
                   f"{len(normalized['tables'])} tables")
        
        return normalized
    
    async def _generate_figure_description(
        self,
        image_bytes: bytes,
        caption: Optional[str] = None,
        page_context: Optional[str] = None,
        section_context: Optional[str] = None,
        elements_text: Optional[str] = None,  # NEW: text inside figure from CU
    ) -> str:
        """
        Generate semantic description for a figure using GPT-4 Vision.
        
        CU provides 'elements' which are text inside the figure - we use this as additional context.
        """
    
    def _extract_figures_from_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract figure references from Content Understanding markdown.
        
        CU embeds figures in markdown as: ![alt](figures/X.Y "AI-generated description")
        where X is page number and Y is figure index on that page.
        
        The AI descriptions can contain:
        - Newlines
        - Single quotes  
        - Hebrew/RTL text
        - Other special characters
        
        Returns list of figure dicts compatible with our pipeline.
        """
        import re
        
        figures = []
        existing_ids = set()
        
        # Match all figure references: ![alt](figures/X.Y followed by anything until )
        # This captures the full content after the figure path
        pattern = r'!\[([^\]]*)\]\(figures/(\d+)\.(\d+)([^)]*)\)'
        
        for match in re.finditer(pattern, markdown):
            alt_text = match.group(1)
            page_num = int(match.group(2))
            fig_index = int(match.group(3))
            rest = match.group(4).strip()  # Everything after X.Y
            
            figure_id = f"{page_num}.{fig_index}"
            
            # Skip duplicates
            if figure_id in existing_ids:
                continue
            existing_ids.add(figure_id)
            
            # Extract AI description from rest: ' "description"' or just the rest
            ai_description = ""
            if rest.startswith('"') and len(rest) > 1:
                # Remove surrounding quotes
                ai_description = rest[1:-1] if rest.endswith('"') else rest[1:]
            elif rest:
                # No quotes, use as-is
                ai_description = rest
            
            # Use alt_text as fallback for caption
            caption = alt_text or (ai_description[:100] if ai_description else "")
            
            figures.append({
                "id": figure_id,
                "caption": caption,
                "ai_description": ai_description,  # CU's AI-generated description (full)
                "elements": [],  # CU doesn't provide elements for markdown figures
                "bounding_regions": [
                    {
                        "page_number": page_num,
                        "polygon": []  # No bounding box from markdown
                    }
                ]
            })
        
        # Sort by page number, then figure index
        figures.sort(key=lambda f: (
            f["bounding_regions"][0]["page_number"] if f["bounding_regions"] else 0,
            int(f["id"].split(".")[-1]) if "." in f["id"] else 0
        ))
        
        logger.info(f"Extracted {len(figures)} figure references from markdown")
        with_desc = sum(1 for f in figures if f.get("ai_description"))
        logger.info(f"  - {with_desc} figures have AI descriptions")
        for fig in figures[:3]:  # Log first 3
            desc_preview = (fig.get("ai_description") or "")[:50]
            logger.info(f"  - Figure {fig['id']}: {desc_preview}...")
        
        return figures

        if not self.openai_client:
            logger.warning("OpenAI client not available for figure description")
            return caption or elements_text or ""
        
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Build prompt with all available context
            prompt_parts = [
                "Describe this image in detail for search indexing. Focus on:",
                "1. What type of image (map, diagram, chart, photo, schematic, table)",
                "2. All visible text, labels, numbers, and identifiers",
                "3. Key entities: place names, station names, product names, people, dates",
                "4. The purpose or meaning of the image in context",
                "",
                "Write the description in the SAME LANGUAGE as the text visible in the image.",
                "If the image contains Hebrew text, respond in Hebrew.",
                "If the image contains English text, respond in English.",
                "Extract ALL numbers and identifiers visible in the image."
            ]
            
            # Add section context
            if section_context:
                prompt_parts.insert(0, f"DOCUMENT SECTION: {section_context}")
                prompt_parts.insert(1, "This image is part of the above section. Keep this context in mind.\n")
            
            # Add CU elements (text inside figure)
            if elements_text:
                prompt_parts.append(f"\nText detected inside this figure: {elements_text}")
            
            if caption:
                prompt_parts.append(f"\nExisting caption: {caption}")
            
            if page_context:
                prompt_parts.append(f"\nPage context: {page_context[:500]}")
            
            prompt = "\n".join(prompt_parts)
            
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
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"Generated figure description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.warning(f"Failed to generate figure description: {e}")
            return caption or elements_text or ""
    
    def _build_page_context(self, cu_result: Dict[str, Any]) -> Dict[int, str]:
        """Build a map of page number -> text context."""
        page_context = {}
        
        for para in cu_result.get("paragraphs", []):
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
    
    def _build_page_section_map(self, cu_result: Dict[str, Any]) -> Dict[int, str]:
        """Build a map of page number -> section header."""
        page_to_section = {}
        current_section = "Introduction"
        last_page_seen = 0
        
        section_starts = []
        
        for para in cu_result.get("paragraphs", []):
            role = para.get("role", "")
            content = para.get("content", "").strip()
            
            if not content:
                continue
            
            for br in para.get("bounding_regions", []):
                page_num = br["page_number"]
                last_page_seen = max(last_page_seen, page_num)
                
                if role in ["sectionHeading", "title"]:
                    section_starts.append((page_num, content))
                    break
        
        section_starts.sort(key=lambda x: x[0])
        
        total_pages = cu_result.get("page_count", last_page_seen)
        
        for page_num in range(1, total_pages + 1):
            current_section = "Introduction"
            for start_page, section_name in section_starts:
                if start_page <= page_num:
                    current_section = section_name
                else:
                    break
            page_to_section[page_num] = current_section
        
        return page_to_section
    
    def _get_elements_text(
        self, 
        elements: List[str], 
        paragraphs: List[Dict]
    ) -> str:
        """
        Extract text from CU elements (references to paragraphs inside figures).
        
        Elements are like: ["/paragraphs/18", "/paragraphs/19", ...]
        """
        texts = []
        para_map = {f"/paragraphs/{i}": p.get("content", "") for i, p in enumerate(paragraphs)}
        
        for elem in elements[:10]:  # Limit to first 10
            if elem in para_map:
                text = para_map[elem]
                if text:
                    texts.append(text)
        
        return " | ".join(texts) if texts else ""
    
    async def _extract_figures(
        self,
        content: bytes,
        cu_result: Dict[str, Any],
        doc_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Extract figures with descriptions.
        
        Content Understanding provides figures in markdown with AI descriptions but no bounding boxes.
        For these, we use the AI descriptions directly without image cropping.
        """
        figures = []
        ext = filename.lower().split(".")[-1]
        
        # Build context maps
        page_to_section = self._build_page_section_map(cu_result)
        
        logger.info(f"Built section map: {len(set(page_to_section.values()))} unique sections")
        
        # Get all figures from CU result (may include markdown-extracted figures)
        all_figures = cu_result.get("figures", [])
        
        logger.info(f"Processing {len(all_figures)} figures from CU result")
        
        # Process each figure - CU figures from markdown have AI descriptions but no bounding boxes
        for i, fig in enumerate(all_figures):
            bounding_regions = fig.get("bounding_regions", [])
            page_nums = [br.get("page_number", 1) for br in bounding_regions]
            page_num = page_nums[0] if page_nums else 1
            section = page_to_section.get(page_num, "")
            
            # Check if we have valid bounding polygon for image cropping
            has_valid_polygon = any(
                len(br.get("polygon", [])) >= 4 for br in bounding_regions
            )
            
            # Get AI description (from CU markdown extraction)
            ai_description = fig.get("ai_description", "") or fig.get("caption", "")
            
            figures.append({
                "id": fig.get("id", f"fig_{i:03d}"),
                "caption": fig.get("caption", ""),
                "description": ai_description,  # Use CU's AI description
                "elements_text": "",
                "page_numbers": page_nums if page_nums else [1],
                "blob_path": None,  # No cropped image for markdown figures
                "section": section,
                "has_bounding_box": has_valid_polygon,
                "source": "markdown" if not has_valid_polygon else "bounding_box"
            })
        
        logger.info(f"Figure extraction complete: {len(figures)} figures")
        
        # Log sample descriptions
        for fig in figures[:3]:
            desc_preview = (fig.get("description") or "")[:60]
            logger.info(f"  - Figure {fig['id']}: {desc_preview}...")
        
        return figures
    
    async def _create_chunks(
        self,
        cu_result: Dict[str, Any],
        doc_id: str,
        filename: str,
        blob_path: str,
        figures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from CU result.
        
        Uses markdown output for text chunking when available.
        """
        chunks = []
        chunk_id = 0
        
        page_to_section = self._build_page_section_map(cu_result)
        
        # 1. Text chunks - prefer markdown if available
        markdown = cu_result.get("markdown", "").strip()
        
        if markdown:
            # Chunk by markdown headers
            chunks.extend(self._chunk_markdown(markdown, doc_id, filename, blob_path, chunk_id))
            chunk_id = len(chunks)
        else:
            # Fallback to paragraph-based chunking
            current_section = "Introduction"
            current_content = []
            current_pages = set()
            
            for para in cu_result.get("paragraphs", []):
                role = para.get("role", "")
                content = para.get("content", "").strip()
                
                if not content:
                    continue
                
                for br in para.get("bounding_regions", []):
                    current_pages.add(br["page_number"])
                
                if role in ["sectionHeading", "title"]:
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
                    
                    current_section = content
                    current_content = []
                    current_pages = set()
                else:
                    current_content.append(content)
            
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
        
        # 2. Table chunks
        for i, table in enumerate(cu_result.get("tables", [])):
            table_md = self._table_to_markdown(table)
            page_nums = [br["page_number"] for br in table.get("bounding_regions", [])]
            table_section = page_to_section.get(page_nums[0] if page_nums else 1, "")
            
            chunks.append({
                "id": f"{doc_id}_table_{i:04d}",
                "content": table_md,
                "content_type": "table",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": page_nums,
                "section_header": table_section,
                "doc_id": doc_id,
                "table_html": self._table_to_html(table)
            })
        
        # 3. Figure chunks
        for fig in figures:
            fig_section = fig.get("section", "")
            
            content_parts = []
            if fig_section:
                content_parts.append(f"Section: {fig_section}")
            if fig.get("description"):
                content_parts.append(fig["description"])
            elif fig.get("elements_text"):
                content_parts.append(f"Figure containing: {fig['elements_text']}")
            elif fig.get("caption"):
                content_parts.append(f"Figure: {fig['caption']}")
            else:
                content_parts.append("Figure")
            
            chunks.append({
                "id": f"{doc_id}_{fig['id']}",
                "content": "\n".join(content_parts),
                "content_type": "figure",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": fig.get("page_numbers", []),
                "section_header": fig_section,
                "doc_id": doc_id,
                "image_blob_path": fig.get("blob_path"),
                "figure_caption": fig.get("caption", "")
            })
        
        # 4. Add AI-generated fields as metadata chunk (if available)
        fields = cu_result.get("fields", {})
        if fields:
            field_content = []
            if fields.get("title"):
                field_content.append(f"Title: {fields['title'].get('valueString', '')}")
            if fields.get("summary"):
                field_content.append(f"Summary: {fields['summary'].get('valueString', '')}")
            if fields.get("key_topics"):
                topics = fields['key_topics'].get('valueArray', [])
                if topics:
                    field_content.append(f"Key Topics: {', '.join(t.get('valueString', '') for t in topics)}")
            
            if field_content:
                chunks.append({
                    "id": f"{doc_id}_metadata",
                    "content": "\n".join(field_content),
                    "content_type": "text",
                    "source_document": filename,
                    "source_document_blob_path": blob_path,
                    "page_numbers": [1],
                    "section_header": "Document Metadata",
                    "doc_id": doc_id
                })
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def _chunk_markdown(
        self, 
        markdown: str, 
        doc_id: str, 
        filename: str, 
        blob_path: str,
        start_chunk_id: int
    ) -> List[Dict[str, Any]]:
        """
        Chunk markdown content by headers.
        
        Simple header-based splitting without LangChain.
        """
        chunks = []
        chunk_id = start_chunk_id
        
        # Split by ## headers (main sections)
        lines = markdown.split("\n")
        current_section = "Introduction"
        current_content = []
        
        for line in lines:
            # Check for headers
            if line.startswith("## "):
                # Save previous section
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        chunks.append({
                            "id": f"{doc_id}_text_{chunk_id:04d}",
                            "content": content,
                            "content_type": "text",
                            "source_document": filename,
                            "source_document_blob_path": blob_path,
                            "page_numbers": [],  # Markdown doesn't have page numbers
                            "section_header": current_section,
                            "doc_id": doc_id
                        })
                        chunk_id += 1
                
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith("# "):
                # Top-level header - also a section break
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        chunks.append({
                            "id": f"{doc_id}_text_{chunk_id:04d}",
                            "content": content,
                            "content_type": "text",
                            "source_document": filename,
                            "source_document_blob_path": blob_path,
                            "page_numbers": [],
                            "section_header": current_section,
                            "doc_id": doc_id
                        })
                        chunk_id += 1
                
                current_section = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Don't forget last section
        if current_content:
            content = "\n".join(current_content).strip()
            if content:
                chunks.append({
                    "id": f"{doc_id}_text_{chunk_id:04d}",
                    "content": content,
                    "content_type": "text",
                    "source_document": filename,
                    "source_document_blob_path": blob_path,
                    "page_numbers": [],
                    "section_header": current_section,
                    "doc_id": doc_id
                })
        
        return chunks
    
    def _table_to_markdown(self, table: Dict[str, Any]) -> str:
        """Convert table to markdown format."""
        rows = [[None] * table.get("column_count", 1) for _ in range(table.get("row_count", 1))]
        
        for cell in table.get("cells", []):
            r, c = cell.get("row_index", 0), cell.get("column_index", 0)
            if r < len(rows) and c < len(rows[0]):
                rows[r][c] = cell.get("content", "")
        
        lines = []
        for i, row in enumerate(rows):
            line = "| " + " | ".join(str(c or "") for c in row) + " |"
            lines.append(line)
            if i == 0:
                lines.append("| " + " | ".join("---" for _ in row) + " |")
        
        return "\n".join(lines)
    
    def _table_to_html(self, table: Dict[str, Any]) -> str:
        """Convert table to HTML format."""
        rows = [[None] * table.get("column_count", 1) for _ in range(table.get("row_count", 1))]
        
        for cell in table.get("cells", []):
            r, c = cell.get("row_index", 0), cell.get("column_index", 0)
            if r < len(rows) and c < len(rows[0]):
                rows[r][c] = cell.get("content", "")
        
        html = ["<table>"]
        for i, row in enumerate(rows):
            html.append("<tr>")
            tag = "th" if i == 0 else "td"
            for cell in row:
                html.append(f"<{tag}>{cell or ''}</{tag}>")
            html.append("</tr>")
        html.append("</table>")
        
        return "".join(html)
