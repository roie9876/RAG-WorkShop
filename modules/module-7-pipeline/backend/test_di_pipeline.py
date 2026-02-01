"""Test DI-based document processor with figure extraction."""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_di_pipeline():
    print("=" * 60)
    print("Testing DI-based Document Processor")
    print("=" * 60)
    
    # 1. Check imports
    print("\n1. Checking dependencies...")
    try:
        from services.document_processor import DocumentProcessor, DI_AVAILABLE, PILLOW_AVAILABLE, OPENAI_AVAILABLE
        print(f"   ✅ DocumentProcessor imported")
        print(f"   - DI SDK: {'✅' if DI_AVAILABLE else '❌'}")
        print(f"   - Pillow: {'✅' if PILLOW_AVAILABLE else '❌'}")
        print(f"   - OpenAI: {'✅' if OPENAI_AVAILABLE else '❌'}")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return
    
    # 2. Initialize processor
    print("\n2. Initializing DocumentProcessor...")
    try:
        processor = DocumentProcessor()
        print(f"   ✅ Processor initialized")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # 3. Load test PDF
    print("\n3. Loading test PDF...")
    try:
        with open('testpdf.pdf', 'rb') as f:
            content = f.read()
        print(f"   ✅ Loaded testpdf.pdf ({len(content)/1024:.1f} KB)")
    except FileNotFoundError:
        print("   ❌ testpdf.pdf not found")
        return
    
    # 4. Analyze with DI
    print("\n4. Analyzing with Document Intelligence...")
    try:
        di_result = await processor._analyze_with_di(content, "testpdf.pdf")
        print(f"   ✅ DI analysis complete")
        print(f"   - Pages: {len(di_result.get('pages', []))}")
        print(f"   - Paragraphs: {len(di_result.get('paragraphs', []))}")
        print(f"   - Tables: {len(di_result.get('tables', []))}")
        print(f"   - Figures: {len(di_result.get('figures', []))}")
    except Exception as e:
        print(f"   ❌ DI analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Check figure bounding boxes
    figures = di_result.get('figures', [])
    print(f"\n5. Checking figure bounding boxes...")
    if figures:
        with_bbox = sum(1 for f in figures if f.get('bounding_regions'))
        print(f"   ✅ {with_bbox}/{len(figures)} figures have bounding boxes")
        
        # Show first figure
        fig = figures[0]
        print(f"\n   Sample figure:")
        print(f"   - ID: {fig.get('id')}")
        caption = fig.get('caption') or {}
        print(f"   - Caption: {caption.get('content', 'N/A')[:50] if caption else 'N/A'}")
        if fig.get('bounding_regions'):
            br = fig['bounding_regions'][0]
            print(f"   - Page: {br.get('page_number')}")
            polygon = br.get('polygon', [])
            if polygon:
                print(f"   - Polygon: [{polygon[0]:.1f}, {polygon[1]:.1f}, ...] ({len(polygon)} points)")
    else:
        print(f"   ⚠️ No figures found")
    
    # 6. Test figure cropping (if we have PyMuPDF)
    print(f"\n6. Testing figure cropping...")
    try:
        import fitz  # PyMuPDF
        print(f"   ✅ PyMuPDF available")
        
        if figures and figures[0].get('bounding_regions'):
            doc = fitz.open(stream=content, filetype="pdf")
            fig = figures[0]
            br = fig['bounding_regions'][0]
            page_num = br['page_number'] - 1  # 0-indexed
            polygon = br['polygon']
            
            # DI polygon is in inches, PyMuPDF expects points (1 inch = 72 points)
            page = doc[page_num]
            
            # Convert polygon to rect
            x_coords = [polygon[i] * 72 for i in range(0, len(polygon), 2)]
            y_coords = [polygon[i] * 72 for i in range(1, len(polygon), 2)]
            rect = fitz.Rect(min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            
            # Crop
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            clip = page.get_pixmap(matrix=mat, clip=rect)
            img_bytes = clip.tobytes("png")
            
            print(f"   ✅ Cropped figure: {len(img_bytes)} bytes")
            
            # Save sample
            with open('output/sample_cropped_figure.png', 'wb') as f:
                f.write(img_bytes)
            print(f"   ✅ Saved to output/sample_cropped_figure.png")
            
            doc.close()
        else:
            print(f"   ⚠️ No figures with bounding boxes to crop")
            
    except ImportError:
        print(f"   ❌ PyMuPDF not installed (pip install pymupdf)")
    except Exception as e:
        print(f"   ❌ Cropping failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_di_pipeline())
