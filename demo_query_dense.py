#!/usr/bin/env python3
"""
查询演示 (纯Dense检索) - 使用DenseRetriever展示向量相似度查询
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.settings import get_settings
from src.core.query_engine.dense_retriever import DenseRetriever

def main():
    """Perform pure dense retrieval on ingested PDFs."""
    print("=" * 80)
    print("DENSE RETRIEVAL QUERY DEMONSTRATION (纯向量相似度检索)")
    print("=" * 80)
    
    settings = get_settings()
    
    # Initialize dense retriever
    try:
        retriever = DenseRetriever(settings, collection_name="ingested_documents")
    except Exception as e:
        print(f"❌ Failed to initialize retriever: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Example query list
    test_queries = [
        "How to make espresso?",
        "Cleaning and maintenance",
        "Water temperature settings",
        "How to use milk frother",
        "Error codes troubleshooting",
    ]
    
    print(f"\n📊 Collection: ingested_documents")
    print(f"🎯 Retriever: DenseRetriever (向量相似度)")
    print(f"📝 Running {len(test_queries)} test queries\n")
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Query {idx}: {query}")
        print(f"{'─' * 80}")
        
        try:
            # Execute dense retrieval
            results = retriever.retrieve(query, top_k=3)
            
            if not results:
                print("❌ No relevant results found")
                continue
            
            print(f"✅ Found {len(results)} relevant documents:\n")
            
            for rank, result in enumerate(results, 1):
                print(f"{rank}. Relevance Score: {result.score:.4f}")
                print(f"   Source: {result.metadata.get('source', 'unknown')}")
                print(f"   Title: {result.metadata.get('title', 'N/A')[:70]}")
                print(f"   Tags: {result.metadata.get('tags', [])}")
                
                # Show fuller content
                content_preview = result.content[:400] if len(result.content) > 400 else result.content
                print(f"   Content: {content_preview}{'...' if len(result.content) > 400 else ''}")
                print()
        
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ Query demonstration completed!")
    print("=" * 80)
    
    # Interactive mode
    print("\n💡 Interactive Query Mode (type 'exit' to quit):")
    while True:
        user_query = input("\n🔍 Enter query > ").strip()
        
        if user_query.lower() == 'exit':
            print("👋 Goodbye!")
            break
        
        if not user_query:
            continue
        
        try:
            results = retriever.retrieve(user_query, top_k=5)
            
            if not results:
                print("❌ No results found")
                continue
            
            print(f"\n✅ Found {len(results)} results:\n")
            for rank, result in enumerate(results, 1):
                print(f"{rank}. Score: {result.score:.4f}")
                print(f"   Source: {result.metadata.get('source', 'N/A')}")
                print(f"   Title: {result.metadata.get('title', 'N/A')[:60]}")
                
                # Fuller content display
                content_preview = result.content[:400] if len(result.content) > 300 else result.content
                print(f"   Content: {content_preview}{'...' if len(result.content) > 300 else ''}")
                print()
        
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    sys.exit(main())
