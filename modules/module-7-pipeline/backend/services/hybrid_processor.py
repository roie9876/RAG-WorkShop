"""
Hybrid Document Processor: DI for Images + CU for Intelligence.

This processor combines the best of both services:
- Document Intelligence (DI): Provides bounding boxes for figure cropping
- Content Understanding (CU): Provides AI descriptions, better markdown, semantic fields

Figure Matching Strategy:
- Both services are called with the same document
- Figures are matched by page number + order within page
- DI provides: bounding boxes, polygon coordinates for cropping
- CU provides: AI-generated descriptions from markdown
- Merged figure has both: cropped image in blob + AI description for search
"""

import io
import logging
import base64
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    DI_AVAILABLE = True
except ImportError:
    DI_AVAILABLE = False

from config.settings import get_settings
from services.blob_service import BlobService
from services.search_service import SearchService
from services.content_understanding_client import AzureContentUnderstandingClient

logger = logging.getLogger(__name__)


class HybridProcessor:
    """
    Hybrid document processor using DI + CU.
    
    Processing Flow:
    1. Analyze with DI → Get figures with bounding boxes
    2. Analyze with CU → Get AI descriptions + markdown
    3. Match figures by page + order
    4. Crop images using DI bounding boxes
    5. Use CU descriptions for search indexing
    6. Store cropped images in blob
    7. Index chunks with both image paths AND descriptions
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_service = BlobService()
        self.search_service = SearchService()
        self._di_client = None
        self._cu_client = None
        logger.info(f"HybridProcessor initialized (DI: {DI_AVAILABLE}, Pillow: {PILLOW_AVAILABLE})")
    
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
    
    @property
    def cu_client(self):
        """Get Content Understanding client."""
        if self._cu_client is None:
            endpoint = self.settings.azure_content_understanding_endpoint
            if not endpoint:
                endpoint = self.settings.azure_document_intelligence_endpoint
            
            key = self.settings.azure_content_understanding_key
            if not key:
                key = getattr(self.settings, 'azure_ai_services_key', '')
            if not key:
                key = self.settings.azure_document_intelligence_key
            
            api_version = self.settings.azure_content_understanding_api_version
            
            self._cu_client = AzureContentUnderstandingClient(
                endpoint=endpoint,
                subscription_key=key,
                api_version=api_version,
            )
            logger.info(f"Created CU client for {endpoint}")
        return self._cu_client
    
    async def process_document(
        self,
        blob_path: str,
        content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process document with hybrid DI + CU approach.
        
        Args:
            blob_path: Path where document is stored in blob
            content: Document content as bytes
            filename: Original filename
            
        Returns:
            Processing result with counts
        """
        doc_id = Path(filename).stem
        
        logger.info(f"=== HYBRID PROCESSING: {filename} ===")
        logger.info(f"Step 1: Parallel analysis with DI and CU...")
        
        # 1. Analyze with BOTH services in parallel
        di_result, cu_result = await asyncio.gather(
            self._analyze_with_di(content, filename),
            self._analyze_with_cu(content, filename)
        )
        
        logger.info(f"  DI: {len(di_result.get('figures', []))} figures with bounding boxes")
        logger.info(f"  CU: markdown with embedded figure descriptions")
        
        # 2. Extract CU figure descriptions from markdown
        cu_figures = self._extract_figures_from_markdown(cu_result.get("markdown", ""))
        logger.info(f"  CU markdown figures: {len(cu_figures)}")
        
        # 3. Match and merge figures
        logger.info(f"Step 2: Matching figures between DI and CU...")
        merged_figures = self._match_figures(di_result.get("figures", []), cu_figures)
        logger.info(f"  Merged: {len(merged_figures)} figures")
        
        # 4. Crop and store images (using DI bounding boxes)
        logger.info(f"Step 3: Cropping and storing figure images...")
        figures = await self._crop_and_store_figures(
            content, merged_figures, di_result, doc_id, filename
        )
        
        # 5. Create chunks with CU markdown for text
        logger.info(f"Step 4: Creating chunks...")
        chunks = await self._create_chunks(
            cu_result, di_result, doc_id, filename, blob_path, figures
        )
        
        # 6. Index chunks
        logger.info(f"Step 5: Indexing {len(chunks)} chunks...")
        await self.search_service.index_chunks(chunks)
        
        return {
            "chunks_created": len(chunks),
            "figures_extracted": len(figures),
            "figures_with_images": sum(1 for f in figures if f.get("blob_path")),
            "figures_with_descriptions": sum(1 for f in figures if f.get("ai_description")),
            "tables_found": len(di_result.get("tables", [])),
            "pages": di_result.get("page_count", 0),
            "processing_mode": "hybrid_di_cu"
        }
    
    async def _analyze_with_di(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document with Document Intelligence to get bounding boxes."""
        ext = filename.lower().split(".")[-1]
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
        
        logger.info(f"  Analyzing with DI: {filename}")
        poller = self.di_client.begin_analyze_document(
            "prebuilt-layout",
            body=content,
            content_type=content_type_map.get(ext, "application/pdf"),
        )
        
        result = poller.result()
        
        # Convert to dict
        return {
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
                        {"page_number": br.page_number, "polygon": br.polygon}
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
                        {"page_number": br.page_number, "polygon": br.polygon}
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
                        {"page_number": br.page_number, "polygon": br.polygon}
                        for br in (fig.bounding_regions or [])
                    ]
                }
                for fig in (result.figures or [])
            ],
            "page_count": len(result.pages) if result.pages else 0
        }
    
    async def _analyze_with_cu(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document with Content Understanding to get AI descriptions."""
        logger.info(f"  Analyzing with CU: {filename}")
        
        ext = filename.lower().split(".")[-1]
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
        
        # Use analyze_document which handles both begin + poll
        result = self.cu_client.analyze_document(
            analyzer_id="prebuilt-layout",  # Use layout for figures
            file_content=content,
            content_type=content_type_map.get(ext, "application/pdf"),
            timeout_seconds=300,
        )
        
        # Status can be "succeeded" or "Succeeded" depending on API response
        status = result.get("status", "").lower()
        if status != "succeeded":
            logger.error(f"CU analysis failed with status '{result.get('status')}': {result}")
            return {"markdown": "", "pages": [], "figures": []}
        
        # CU result structure for prebuilt-layout (API 2025-11-01):
        # result.result.contents[0].markdown (in an array)
        inner_result = result.get("result", {})
        
        # Get markdown from contents array
        markdown = ""
        contents = inner_result.get("contents", [])
        for c in contents:
            if "markdown" in c:
                markdown += c.get("markdown", "") + "\n\n"
        
        # Fallback: try direct markdown (older API style)
        if not markdown:
            markdown = inner_result.get("markdown", "")
        
        logger.info(f"  CU markdown: {len(markdown)} chars, figures embedded in markdown")
        
        return {
            "markdown": markdown,
            "pages": inner_result.get("pages", []),
            "figures": inner_result.get("figures", [])  # Usually empty for CU
        }
    
    def _extract_figures_from_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract figure references from CU markdown.
        
        CU embeds figures as: ![alt](figures/PAGE.INDEX "AI description")
        """
        import re
        
        figures = []
        existing_ids = set()
        
        # Match: ![alt](figures/X.Y followed by anything until )
        pattern = r'!\[([^\]]*)\]\(figures/(\d+)\.(\d+)([^)]*)\)'
        
        for match in re.finditer(pattern, markdown):
            alt_text = match.group(1)
            page_num = int(match.group(2))
            fig_index = int(match.group(3))
            rest = match.group(4).strip()
            
            figure_id = f"{page_num}.{fig_index}"
            
            if figure_id in existing_ids:
                continue
            existing_ids.add(figure_id)
            
            # Extract AI description from rest
            ai_description = ""
            if rest.startswith('"') and len(rest) > 1:
                ai_description = rest[1:-1] if rest.endswith('"') else rest[1:]
            elif rest:
                ai_description = rest
            
            figures.append({
                "id": figure_id,
                "page_number": page_num,
                "index_on_page": fig_index,
                "alt_text": alt_text,
                "ai_description": ai_description,
                "source": "cu_markdown"
            })
        
        # Sort by page, then index
        figures.sort(key=lambda f: (f["page_number"], f["index_on_page"]))
        
        logger.info(f"  Extracted {len(figures)} figures from CU markdown")
        return figures
    
    def _match_figures(
        self,
        di_figures: List[Dict[str, Any]],
        cu_figures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match figures from DI and CU by page number + order.
        
        Strategy:
        1. Group DI figures by page number (they have sequential IDs like figure-0)
        2. Group CU figures by page number (they have page.index IDs)
        3. Match by order within each page
        4. Merge: DI bounding box + CU description
        """
        # Group DI figures by page
        di_by_page = defaultdict(list)
        for fig in di_figures:
            for br in fig.get("bounding_regions", []):
                page = br.get("page_number", 1)
                di_by_page[page].append({
                    **fig,
                    "_page": page,
                    "_polygon": br.get("polygon", [])
                })
        
        # Sort DI figures within each page by Y position (top to bottom)
        for page in di_by_page:
            di_by_page[page].sort(key=lambda f: f["_polygon"][1] if len(f["_polygon"]) > 1 else 0)
        
        # Group CU figures by page
        cu_by_page = defaultdict(list)
        for fig in cu_figures:
            cu_by_page[fig["page_number"]].append(fig)
        
        # Sort CU figures by index (already ordered by page.index format)
        for page in cu_by_page:
            cu_by_page[page].sort(key=lambda f: f["index_on_page"])
        
        # Match figures
        merged = []
        all_pages = set(di_by_page.keys()) | set(cu_by_page.keys())
        
        match_stats = {"matched": 0, "di_only": 0, "cu_only": 0}
        
        for page in sorted(all_pages):
            di_figs = di_by_page.get(page, [])
            cu_figs = cu_by_page.get(page, [])
            
            # Match by index
            max_len = max(len(di_figs), len(cu_figs))
            
            for i in range(max_len):
                di_fig = di_figs[i] if i < len(di_figs) else None
                cu_fig = cu_figs[i] if i < len(cu_figs) else None
                
                merged_fig = {
                    "page_number": page,
                    "index_on_page": i + 1,
                    "bounding_regions": [],
                    "polygon": [],
                    "ai_description": "",
                    "caption": "",
                    "di_id": None,
                    "cu_id": None,
                    "match_type": "unknown"
                }
                
                if di_fig and cu_fig:
                    # Perfect match
                    merged_fig["bounding_regions"] = di_fig.get("bounding_regions", [])
                    merged_fig["polygon"] = di_fig.get("_polygon", [])
                    merged_fig["caption"] = di_fig.get("caption", "")
                    merged_fig["ai_description"] = cu_fig.get("ai_description", "")
                    merged_fig["di_id"] = di_fig.get("id")
                    merged_fig["cu_id"] = cu_fig.get("id")
                    merged_fig["match_type"] = "matched"
                    match_stats["matched"] += 1
                    
                elif di_fig:
                    # DI only - has bounding box but no AI description
                    merged_fig["bounding_regions"] = di_fig.get("bounding_regions", [])
                    merged_fig["polygon"] = di_fig.get("_polygon", [])
                    merged_fig["caption"] = di_fig.get("caption", "")
                    merged_fig["di_id"] = di_fig.get("id")
                    merged_fig["match_type"] = "di_only"
                    match_stats["di_only"] += 1
                    
                elif cu_fig:
                    # CU only - has AI description but no bounding box
                    merged_fig["ai_description"] = cu_fig.get("ai_description", "")
                    merged_fig["cu_id"] = cu_fig.get("id")
                    merged_fig["match_type"] = "cu_only"
                    match_stats["cu_only"] += 1
                
                # Generate unified ID
                merged_fig["id"] = f"fig_p{page}_{i+1}"
                merged.append(merged_fig)
        
        logger.info(f"  Figure matching: {match_stats}")
        return merged
    
    async def _crop_and_store_figures(
        self,
        content: bytes,
        merged_figures: List[Dict[str, Any]],
        di_result: Dict[str, Any],
        doc_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Crop figures using DI bounding boxes and store in blob.
        """
        if not PILLOW_AVAILABLE:
            logger.warning("Pillow not available - skipping image cropping")
            return merged_figures
        
        ext = filename.lower().split(".")[-1]
        if ext != "pdf":
            logger.info("  Non-PDF files don't support figure cropping yet")
            return merged_figures
        
        try:
            from pdf2image import convert_from_bytes
            
            # Convert PDF to images
            logger.info(f"  Converting PDF to images...")
            page_images = convert_from_bytes(content, dpi=150)
            
            # Get page dimensions from DI
            page_dims = {
                p["page_number"]: (p["width"], p["height"])
                for p in di_result.get("pages", [])
            }
            
            cropped_count = 0
            
            for fig in merged_figures:
                polygon = fig.get("polygon", [])
                page_num = fig.get("page_number", 1)
                
                # Skip if no valid polygon
                if len(polygon) < 4:
                    continue
                
                if page_num > len(page_images):
                    continue
                
                page_image = page_images[page_num - 1]
                
                # Get page dimensions for scaling
                di_width, di_height = page_dims.get(page_num, (8.5, 11))
                img_width, img_height = page_image.size
                
                # Scale polygon to image coordinates
                scale_x = img_width / di_width
                scale_y = img_height / di_height
                
                # Get bounding box from polygon
                x_coords = [polygon[i] * scale_x for i in range(0, len(polygon), 2)]
                y_coords = [polygon[i] * scale_y for i in range(1, len(polygon), 2)]
                
                left = max(0, int(min(x_coords)) - 5)
                top = max(0, int(min(y_coords)) - 5)
                right = min(img_width, int(max(x_coords)) + 5)
                bottom = min(img_height, int(max(y_coords)) + 5)
                
                # Crop image
                cropped = page_image.crop((left, top, right, bottom))
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                cropped.save(img_buffer, format="PNG")
                img_bytes = img_buffer.getvalue()
                
                # Upload to blob
                blob_path = f"figures/{doc_id}/{fig['id']}.png"
                await self.blob_service.upload_bytes(blob_path, img_bytes, "image/png")
                
                fig["blob_path"] = blob_path
                cropped_count += 1
            
            logger.info(f"  Cropped and stored {cropped_count} figure images")
            
        except ImportError:
            logger.warning("pdf2image not available - skipping image cropping")
        except Exception as e:
            logger.error(f"Error cropping figures: {e}")
        
        return merged_figures
    
    async def _create_chunks(
        self,
        cu_result: Dict[str, Any],
        di_result: Dict[str, Any],
        doc_id: str,
        filename: str,
        blob_path: str,
        figures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks using CU markdown for text, DI for tables.
        """
        chunks = []
        chunk_id = 0
        
        # Build page-to-section map from DI paragraphs
        page_to_section = self._build_page_section_map(di_result)
        
        # 1. Text chunks from CU markdown
        markdown = cu_result.get("markdown", "").strip()
        if markdown:
            text_chunks = self._chunk_markdown(markdown, doc_id, filename, blob_path, chunk_id)
            chunks.extend(text_chunks)
            chunk_id = len(chunks)
            logger.info(f"  Created {len(text_chunks)} text chunks from markdown")
        
        # 2. Table chunks from DI (better structure)
        for i, table in enumerate(di_result.get("tables", [])):
            page_nums = [br["page_number"] for br in table.get("bounding_regions", [])]
            section = page_to_section.get(page_nums[0] if page_nums else 1, "")
            
            chunks.append({
                "id": f"{doc_id}_table_{i:04d}",
                "content": self._table_to_markdown(table),
                "content_type": "table",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": page_nums,
                "section_header": section,
                "doc_id": doc_id
            })
        
        logger.info(f"  Created {len(di_result.get('tables', []))} table chunks")
        
        # 3. Figure chunks with both image paths AND descriptions
        for fig in figures:
            section = page_to_section.get(fig.get("page_number", 1), "")
            
            # Build rich content for search
            content_parts = []
            if section:
                content_parts.append(f"Section: {section}")
            if fig.get("ai_description"):
                content_parts.append(fig["ai_description"])  # CU's AI description
            elif fig.get("caption"):
                content_parts.append(f"Figure: {fig['caption']}")  # DI caption
            else:
                content_parts.append("Figure")
            
            chunks.append({
                "id": f"{doc_id}_{fig['id']}",
                "content": "\n".join(content_parts),
                "content_type": "figure",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": [fig.get("page_number", 1)],
                "section_header": section,
                "doc_id": doc_id,
                "image_blob_path": fig.get("blob_path"),  # DI-cropped image
                "figure_caption": fig.get("caption", ""),
                "match_type": fig.get("match_type", "unknown")
            })
        
        logger.info(f"  Created {len(figures)} figure chunks")
        logger.info(f"  Total chunks: {len(chunks)}")
        
        return chunks
    
    def _build_page_section_map(self, di_result: Dict[str, Any]) -> Dict[int, str]:
        """Map page numbers to their section headers."""
        page_to_section = {}
        current_section = ""
        
        for para in di_result.get("paragraphs", []):
            role = para.get("role", "")
            if role in ["sectionHeading", "title"]:
                current_section = para.get("content", "")
            
            for br in para.get("bounding_regions", []):
                page = br.get("page_number", 1)
                if page not in page_to_section:
                    page_to_section[page] = current_section
        
        return page_to_section
    
    def _chunk_markdown(
        self,
        markdown: str,
        doc_id: str,
        filename: str,
        blob_path: str,
        start_id: int
    ) -> List[Dict[str, Any]]:
        """Split markdown by headers into chunks."""
        import re
        
        chunks = []
        chunk_id = start_id
        
        # Split by headers (## or #)
        sections = re.split(r'\n(?=#{1,2}\s)', markdown)
        
        current_section = "Introduction"
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Extract header if present
            header_match = re.match(r'^(#{1,2})\s*(.+?)(?:\n|$)', section)
            if header_match:
                current_section = header_match.group(2).strip()
                content = section[header_match.end():].strip()
            else:
                content = section
            
            if not content:
                continue
            
            # Remove figure references from text chunks (they're separate)
            content = re.sub(r'!\[[^\]]*\]\(figures/[^)]+\)', '', content)
            content = content.strip()
            
            if not content:
                continue
            
            chunks.append({
                "id": f"{doc_id}_text_{chunk_id:04d}",
                "content": content,
                "content_type": "text",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": [],  # Would need more processing to determine
                "section_header": current_section,
                "doc_id": doc_id
            })
            chunk_id += 1
        
        return chunks
    
    def _table_to_markdown(self, table: Dict[str, Any]) -> str:
        """Convert DI table to markdown format."""
        rows = table.get("row_count", 0)
        cols = table.get("column_count", 0)
        
        if rows == 0 or cols == 0:
            return ""
        
        # Build grid
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        
        for cell in table.get("cells", []):
            r = cell.get("row_index", 0)
            c = cell.get("column_index", 0)
            if 0 <= r < rows and 0 <= c < cols:
                grid[r][c] = cell.get("content", "").replace("\n", " ")
        
        # Convert to markdown
        lines = []
        for i, row in enumerate(grid):
            lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * cols) + " |")
        
        return "\n".join(lines)
