# Document Processing Utilities
"""
Azure AI Document Intelligence utilities for the RAG Workshop.

This module provides helpers for:
- Analyzing documents with Document Intelligence
- Extracting tables, figures, and paragraphs
- Processing multiple file formats (PDF, Word, Excel, PowerPoint)
"""

# TODO: Implement in Module 2


def analyze_document(file_path: str) -> dict:
    """
    Analyze a document using Azure AI Document Intelligence.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        dict: Analysis result with pages, tables, figures, paragraphs
    """
    raise NotImplementedError("Implement in Module 2")


def extract_tables(analysis_result: dict) -> list:
    """
    Extract tables from Document Intelligence analysis result.
    
    Args:
        analysis_result: Result from analyze_document()
        
    Returns:
        list: List of table dictionaries with structure preserved
    """
    raise NotImplementedError("Implement in Module 2")


def extract_figures(analysis_result: dict) -> list:
    """
    Extract figures with bounding boxes from analysis result.
    
    Args:
        analysis_result: Result from analyze_document()
        
    Returns:
        list: List of figure dictionaries with bounding boxes
    """
    raise NotImplementedError("Implement in Module 2")


def crop_figure(pdf_path: str, bounding_box: dict, page_number: int) -> bytes:
    """
    Crop a figure from a PDF using its bounding box.
    
    Args:
        pdf_path: Path to the PDF file
        bounding_box: Dict with x, y, width, height
        page_number: 1-based page number
        
    Returns:
        bytes: Cropped image as PNG bytes
    """
    raise NotImplementedError("Implement in Module 5")
