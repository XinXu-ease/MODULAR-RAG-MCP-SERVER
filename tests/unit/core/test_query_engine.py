from src.core.query_engine import DenseRetriever, HybridSearch, SparseRetriever


class DummyEmbedding:
    def embed(self, texts, **kwargs):
        return [[0.2, 0.8] for _ in texts]


class DummyVectorStore:
    def __init__(self):
        self.query_payload = [
            {"id": "c1", "distance": 0.1, "metadata": {"source": "a.pdf"}, "text": "alpha"},
            {"id": "c2", "distance": 0.4, "metadata": {"source": "b.pdf"}, "text": "beta"},
        ]
        self.records = {
            "c1": {"id": "c1", "metadata": {"source": "a.pdf"}, "text": "alpha"},
            "c2": {"id": "c2", "metadata": {"source": "b.pdf"}, "text": "beta"},
        }

    def add(self, embeddings, metadatas, ids=None, documents=None):
        return None

    def upsert(self, embeddings, metadatas, ids, documents=None):
        return None

    def query(self, query_embedding, top_k=10):
        return self.query_payload[:top_k]

    def get_by_ids(self, ids):
        return [self.records[item_id] for item_id in ids if item_id in self.records]


class DummyBM25:
    def load(self):
        return None

    def query(self, query, top_k=10):
        return ["c2", "c1"][:top_k]


class ReverseReranker:
    def rerank(self, query, candidates, **kwargs):
        return list(reversed(candidates))


def test_dense_retriever_returns_scored_results():
    retriever = DenseRetriever(
        embedding_model=DummyEmbedding(),
        vector_store=DummyVectorStore(),
    )

    results = retriever.search("hello", top_k=2)

    assert [item.chunk_id for item in results] == ["c1", "c2"]
    assert results[0].score > results[1].score
    assert results[0].score_breakdown["dense"] == results[0].score


def test_sparse_retriever_hydrates_content_from_store():
    retriever = SparseRetriever(
        bm25_indexer=DummyBM25(),
        vector_store=DummyVectorStore(),
    )

    results = retriever.search("hello", top_k=2)

    assert [item.chunk_id for item in results] == ["c2", "c1"]
    assert results[0].content == "beta"
    assert results[0].score_breakdown["sparse"] == 1.0


def test_hybrid_search_fuses_and_reranks_results():
    hybrid = HybridSearch(
        dense_retriever=DenseRetriever(
            embedding_model=DummyEmbedding(),
            vector_store=DummyVectorStore(),
        ),
        sparse_retriever=SparseRetriever(
            bm25_indexer=DummyBM25(),
            vector_store=DummyVectorStore(),
        ),
        reranker=ReverseReranker(),
    )

    result = hybrid.search("hello", top_k=2, use_rerank=True)

    assert [item.chunk_id for item in result.retrieved_chunks] == ["c1", "c2"]
    assert "dense_retrieval" in result.stage_latencies
    assert "sparse_retrieval" in result.stage_latencies
    assert "fusion" in result.stage_latencies
    assert "rerank" in result.stage_latencies
    assert result.retrieved_chunks[0].score_breakdown["rerank"] == 1.0
