"""
Document Processor Service.
Orchestrates DI + CU for document processing.
"""

import io
import logging
from typing import List, Dict, Any

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

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processing with DI (bounding boxes) + CU (semantics).
    
    Flow:
    1. DI extracts layout, tables, figures with bounding boxes
    2. Figures are cropped and stored in blob
    3. CU generates semantic descriptions for figures
    4. Content is chunked by type (text, table, figure)
    5. Chunks are indexed in Azure AI Search
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_service = BlobService()
        self.search_service = SearchService()
        self._di_client = None
        logger.info(f"DocumentProcessor initialized (DI SDK available: {DI_AVAILABLE}, Pillow available: {PILLOW_AVAILABLE})")
    
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
    
    async def process_document(
        self,
        blob_path: str,
        content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process a document end-to-end.
        
        Args:
            blob_path: Path where document is stored in blob
            content: Document content as bytes
            filename: Original filename
            
        Returns:
            Processing result with counts
        """
        # Extract document ID from blob path
        doc_id = blob_path.split("/")[1] if "/" in blob_path else blob_path
        
        # 1. Analyze with Document Intelligence
        di_result = await self._analyze_with_di(content, filename)
        
        # 2. Extract and store figures
        figures = await self._extract_figures(content, di_result, doc_id, filename)
        
        # 3. Create chunks from DI result
        chunks = await self._create_chunks(di_result, doc_id, filename, blob_path, figures)
        
        # 4. Generate embeddings and index chunks
        await self.search_service.index_chunks(chunks)
        
        return {
            "chunks_created": len(chunks),
            "figures_extracted": len(figures),
            "tables_found": len(di_result.get("tables", [])),
            "pages": di_result.get("page_count", 0)
        }
    
    async def _analyze_with_di(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document with Document Intelligence.
        
        Uses prebuilt-layout model to extract:
        - Text with reading order
        - Tables with cell structure
        - Figures with bounding boxes
        """
        # Determine content type
        ext = filename.lower().split(".")[-1]
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
        
        # Analyze document - using prebuilt-layout which includes figures by default
        logger.info(f"Analyzing document with DI: {filename}")
        poller = self.di_client.begin_analyze_document(
            "prebuilt-layout",
            body=content,
            content_type=content_type_map.get(ext, "application/pdf"),
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
        Extract figures using bounding boxes from DI.
        
        For PDFs, converts pages to images and crops.
        For Office files, extracts embedded images.
        """
        figures = []
        ext = filename.lower().split(".")[-1]
        
        if ext != "pdf":
            # For Office files, figure extraction is more complex
            # For now, return figures with captions only
            for i, fig in enumerate(di_result.get("figures", [])):
                figures.append({
                    "id": f"fig_{i:03d}",
                    "caption": fig.get("caption", ""),
                    "description": "",  # Will be filled by CU
                    "page_numbers": [
                        br["page_number"] 
                        for br in fig.get("bounding_regions", [])
                    ],
                    "blob_path": None  # No image for Office files yet
                })
            return figures
        
        # For PDFs, use pdf2image to extract figures
        try:
            from pdf2image import convert_from_bytes
            
            # Convert PDF pages to images
            page_images = convert_from_bytes(content, dpi=150)
            
            for i, fig in enumerate(di_result.get("figures", [])):
                for br in fig.get("bounding_regions", []):
                    page_num = br["page_number"]
                    polygon = br.get("polygon", [])
                    
                    if page_num <= len(page_images) and len(polygon) >= 4:
                        page_img = page_images[page_num - 1]
                        
                        # Get bounding box from polygon
                        # Polygon is list of points [x1,y1,x2,y2,x3,y3,x4,y4]
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
                        
                        # Crop figure
                        cropped = page_img.crop((left, top, right, bottom))
                        
                        # Save to bytes
                        img_buffer = io.BytesIO()
                        cropped.save(img_buffer, format="PNG")
                        img_bytes = img_buffer.getvalue()
                        
                        # Upload to blob
                        figure_id = f"fig_{i:03d}"
                        blob_path = await self.blob_service.upload_figure(
                            img_bytes, doc_id, figure_id
                        )
                        
                        figures.append({
                            "id": figure_id,
                            "caption": fig.get("caption", ""),
                            "description": "",  # Will be filled by CU
                            "page_numbers": [page_num],
                            "blob_path": blob_path,
                            "bounding_box": {
                                "left": left,
                                "top": top,
                                "right": right,
                                "bottom": bottom
                            }
                        })
                        break  # Only process first bounding region
                        
        except ImportError:
            # pdf2image not available
            pass
        except Exception as e:
            print(f"Figure extraction error: {e}")
        
        return figures
    
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
        - table: Each table as atomic chunk
        - figure: Each figure with description
        """
        chunks = []
        chunk_id = 0
        
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
        for i, table in enumerate(di_result.get("tables", [])):
            # Convert table to markdown
            table_md = self._table_to_markdown(table)
            
            page_nums = [
                br["page_number"] 
                for br in table.get("bounding_regions", [])
            ]
            
            chunks.append({
                "id": f"{doc_id}_table_{i:04d}",
                "content": table_md,
                "content_type": "table",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": page_nums,
                "section_header": "",  # Could be enhanced to find nearest section
                "doc_id": doc_id,
                "table_html": self._table_to_html(table)
            })
        
        # 3. Figure chunks
        for fig in figures:
            # Generate description using CU or GPT-4 Vision
            description = fig.get("description", "")
            if not description and fig.get("caption"):
                description = f"Figure showing: {fig['caption']}"
            
            chunks.append({
                "id": f"{doc_id}_{fig['id']}",
                "content": description or f"Figure: {fig.get('caption', 'No caption')}",
                "content_type": "figure",
                "source_document": filename,
                "source_document_blob_path": blob_path,
                "page_numbers": fig.get("page_numbers", []),
                "section_header": "",
                "doc_id": doc_id,
                "image_blob_path": fig.get("blob_path"),
                "figure_caption": fig.get("caption", "")
            })
        
        return chunks
    
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
