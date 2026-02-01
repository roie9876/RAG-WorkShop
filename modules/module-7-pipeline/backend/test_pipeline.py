"""
Full E2E Pipeline Test: DI + GPT-4V + Blob + Search
Tests the complete document processing pipeline.
"""
import asyncio
import json
import sys
sys.path.insert(0, '.')

async def test_full_pipeline():
    print("=" * 70)
    print("Full E2E Pipeline: DI + GPT-4V + Blob + Search")
    print("=" * 70)
    
    from services.document_processor import DocumentProcessor
    from services.search_service import SearchService
    from services.blob_service import BlobService
    
    # Initialize services
    processor = DocumentProcessor()
    search_service = SearchService()
    blob_service = BlobService()
    
    # Load test PDF
    with open('testpdf.pdf', 'rb') as f:
        content = f.read()
    
    filename = "testpdf.pdf"
    blob_path = f"documents/{filename}"
    
    print(f"\n✅ Loaded {filename} ({len(content)/1024:.1f} KB)")
    
    # 0. Recreate index with new schema
    print("\n0. Recreating search index with updated schema...")
    try:
        await search_service.create_index_if_not_exists(force_recreate=True)
        print(f"   ✅ Index recreated: {search_service.settings.azure_search_index_name}")
    except Exception as e:
        print(f"   ⚠️  Index recreation failed: {e}")
    
    # 1. Upload document to blob (optional - just for reference)
    print("\n1. Uploading document to Blob Storage...")
    try:
        doc_url = await blob_service.upload_document(content, blob_path)
        print(f"   ✅ Uploaded to: {doc_url[:80]}...")
    except Exception as e:
        print(f"   ⚠️  Blob upload skipped: {e}")
        doc_url = blob_path
    
    # 2. Process document (DI + GPT-4V + Indexing)
    print("\n2. Processing document with DI + GPT-4V pipeline...")
    print("   (This will crop figures, generate GPT-4V descriptions, and index)")
    
    try:
        result = await processor.process_document(
            blob_path=blob_path,
            content=content,
            filename=filename,
            use_di=True
        )
        print(f"\n   ✅ Processing complete!")
        print(f"   - Doc ID: {result['doc_id']}")
        print(f"   - Pages: {result['page_count']}")
        print(f"   - Total chunks: {result['chunks_created']}")
        print(f"   - Text chunks: {result['text_chunks']}")
        print(f"   - Table chunks: {result['table_chunks']}")
        print(f"   - Figure chunks: {result['figure_chunks']}")
        print(f"   - Mode: {result['processing_mode']}")
    except Exception as e:
        print(f"   ❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Test search
    print("\n3. Testing search queries...")
    
    test_queries = [
        ("BenQ logo", "figure"),
        ("safety warnings electrical", "figure"),
        ("product specifications", "text"),
    ]
    
    for query, expected_type in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            results = await search_service.search(
                query=query,
                top_k=3,
                search_mode="hybrid"
            )
            
            if results:
                print(f"   ✅ Found {len(results)} results:")
                for r in results[:2]:
                    content_preview = r['content'][:80].replace('\n', ' ')
                    print(f"      - [{r['content_type']}] {content_preview}...")
                    if r.get('image_blob_path'):
                        print(f"        🖼️  Image: {r['image_blob_path']}")
            else:
                print(f"   ⚠️  No results found")
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
    
    # 4. Test figure-specific search
    print("\n4. Testing figure search...")
    try:
        results = await search_service.search(
            query="warning symbol triangle",
            top_k=5,
            content_type_filter="figure"
        )
        
        if results:
            print(f"   ✅ Found {len(results)} figure results:")
            for r in results[:3]:
                print(f"\n   Figure: {r['id']}")
                print(f"   Section: {r.get('section_header', 'N/A')}")
                print(f"   Image: {r.get('image_blob_path', 'N/A')}")
                content_preview = r['content'][:150].replace('\n', ' ')
                print(f"   Content: {content_preview}...")
        else:
            print(f"   ⚠️  No figure results found")
    except Exception as e:
        print(f"   ❌ Figure search failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Full Pipeline Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
