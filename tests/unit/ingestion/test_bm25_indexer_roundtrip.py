from src.ingestion.storage.bm25_indexer import BM25Indexer


def test_bm25_indexer_roundtrip(tmp_path):
    indexer = BM25Indexer(index_dir=str(tmp_path / "bm25"))
    sparse_vectors = {
        "c1": {"coffee": 0.7, "brew": 0.3},
        "c2": {"tea": 1.0},
    }
    indexer.build(sparse_vectors)

    loaded = BM25Indexer(index_dir=str(tmp_path / "bm25"))
    loaded.load()
    top = loaded.query("coffee brew", top_k=1)
    assert top[0] == "c1"
