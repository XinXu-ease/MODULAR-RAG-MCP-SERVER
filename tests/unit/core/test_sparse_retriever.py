from src.core.query_engine.sparse_retriever import SparseRetriever


class DummyBM25:
    def __init__(self):
        self.loaded = False
        self.calls = []

    def load(self):
        self.loaded = True

    def query_with_scores(self, query_text, top_k=5):
        self.calls.append((query_text, top_k))
        return [("c2", 3.0), ("c1", 1.5)]


class DummyVectorStore:
    def add(self, embeddings, metadatas, ids=None, documents=None):
        return None

    def upsert(self, embeddings, metadatas, ids, documents=None):
        return None

    def query(self, query_embedding, top_k=10):
        return []

    def get_by_ids(self, ids):
        return [
            {"id": "c1", "text": "sparse text 1", "metadata": {"doc_type": "pdf"}},
            {"id": "c2", "text": "sparse text 2", "metadata": {"doc_type": "web"}},
        ]


def test_sparse_retriever_loads_and_merges(sample_settings):
    bm25 = DummyBM25()
    retriever = SparseRetriever(settings=sample_settings, bm25_indexer=bm25, vector_store=DummyVectorStore())

    results = retriever.retrieve(["hybrid", "search"], top_k=2)

    assert bm25.loaded is True
    assert bm25.calls[0] == ("hybrid search", 2)
    assert [r.chunk_id for r in results] == ["c2", "c1"]
    assert results[0].content == "sparse text 2"


def test_sparse_retriever_empty_keywords_returns_empty(sample_settings):
    retriever = SparseRetriever(settings=sample_settings, bm25_indexer=DummyBM25(), vector_store=DummyVectorStore())
    assert retriever.retrieve([], top_k=3) == []
