"""Inspect actual chunks stored in the database."""

import sys
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform.startswith('win'):
    import os
    os.system('chcp 65001 > nul')

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.libs.vector_store.vector_store_factory import create_vector_store
from src.core.settings import get_settings

settings = get_settings()
vector_store = create_vector_store(settings, collection_name="ingested_documents")

# Query to inspect actual chunks
results = vector_store.query(
    query_embedding=[0.1] * 1536,  # Dummy embedding
    top_k=10
)

print("=" * 80)
print("ACTUAL CHUNKS IN DATABASE")
print("=" * 80)

for i, result in enumerate(results, 1):
    print(f"\nChunk {i}:")
    print(f"ID: {result['id'][:20]}...")
    print(f"Distance: {result['distance']:.4f}")
    try:
        source = result['metadata'].get('source', 'unknown')
        chunk_idx = result['metadata'].get('chunk_index', '?')
        print(f"Source: chunk #{chunk_idx}")
    except:
        print(f"Source: (unknown)")
    
    print(f"Content ({len(result['text'])} chars):")
    print("-" * 80)
    # Safe print - handle encoding issues
    content = result['text'][:300]
    try:
        print(content[:200])
    except:
        print("[Content - encoding issue]")
    print("-" * 80)
