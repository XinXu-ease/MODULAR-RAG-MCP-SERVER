#!/usr/bin/env python3
"""
检查当前chunks的metadata内容
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.settings import get_settings
from src.libs.vector_store.vector_store_factory import create_vector_store

def main():
    """Inspect metadata in stored chunks."""
    settings = get_settings()
    
    print("=" * 80)
    print("METADATA INSPECTION")
    print("=" * 80)
    
    # Get vector store
    vector_store = create_vector_store(settings, collection_name="ingested_documents")
    
    # Query all documents
    print("\n📊 Fetching all stored chunks...")
    results = vector_store.query(query_embedding=[0.0] * 1536, top_k=1000)  # Get many results
    
    if not results:
        print("❌ No chunks found in vector store")
        return 1
    
    print(f"\n✅ Found {len(results)} chunks\n")
    
    # Analyze metadata structure
    metadata_keys = set()
    metadata_samples = {}
    
    for i, result in enumerate(results[:10], 1):
        metadata = result.get("metadata", {})
        print(f"\n{'─' * 80}")
        print(f"Chunk {i}:")
        print(f"  ID: {result.get('id')[:40]}...")
        print(f"  Text: {(result.get('text') or '')[:100]}...")
        print(f"\n  Metadata ({len(metadata)} fields):")
        
        for key, value in metadata.items():
            value_str = str(value)[:60]
            print(f"    - {key}: {value_str}")
            metadata_keys.add(key)
            if key not in metadata_samples:
                metadata_samples[key] = value
    
    print(f"\n\n{'=' * 80}")
    print("METADATA STRUCTURE SUMMARY")
    print("=" * 80)
    print(f"\nAll unique metadata keys ({len(metadata_keys)}):")
    for key in sorted(metadata_keys):
        print(f"  - {key}")
    
    print("\n\n" + "=" * 80)
    print("QUERY WITH METADATA FILTERING EXAMPLE")
    print("=" * 80)
    
    # Test query with filter
    from src.core.query_engine.dense_retriever import DenseRetriever
    from src.libs.embedding.embedding_factory import create_embedding
    
    retriever = DenseRetriever(settings, collection_name="ingested_documents")
    
    # Query without filter
    query = "espresso"
    print(f"\n🔍 Query: '{query}'")
    print(f"   WITHOUT filter:")
    results_no_filter = retriever.retrieve(query, top_k=3, filters=None)
    for i, r in enumerate(results_no_filter, 1):
        print(f"   {i}. Score: {r.score:.4f}, Source: {r.metadata.get('source', 'N/A')}")
    
    # Query with filter (if applicable)
    if results:
        first_source = results[0].get("metadata", {}).get("source")
        if first_source:
            print(f"\n   WITH filter (source='{first_source}'):")
            results_with_filter = retriever.retrieve(query, top_k=3, filters={"source": first_source})
            for i, r in enumerate(results_with_filter, 1):
                print(f"   {i}. Score: {r.score:.4f}, Source: {r.metadata.get('source', 'N/A')}")
    
    print("\n\n" + "=" * 80)
    print("FINDINGS")
    print("=" * 80)
    print("""
1. ✅ Metadata is stored with each chunk
2. DenseRetriever supports filters via _matches_filters() method
3. HybridSearch doesn't currently pass filters to retrievers
4. Consider: Adding optional metadata filters to search interface
""")

if __name__ == "__main__":
    sys.exit(main())
