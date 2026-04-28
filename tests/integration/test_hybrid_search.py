from src.core.query_engine.hybrid_search import HybridSearch
from src.core.query_engine.query_processor import QueryProcessor
from src.core.types import RetrievalResult


class DenseOK:
    def retrieve(self, query, top_k, filters=None, trace=None):
        return [
            RetrievalResult(chunk_id="a", content="dense a", metadata={"collection": "spec"}, score=0.9),
            RetrievalResult(chunk_id="b", content="dense b", metadata={"collection": "spec"}, score=0.8),
        ]


class DenseFail:
    def retrieve(self, query, top_k, filters=None, trace=None):
        raise RuntimeError("dense unavailable")


class SparseOK:
    def retrieve(self, keywords, top_k, trace=None):
        return [
            RetrievalResult(chunk_id="b", content="sparse b", metadata={"collection": "spec"}, score=0.9),
            RetrievalResult(chunk_id="c", content="sparse c", metadata={"collection": "other"}, score=0.7),
        ]


def test_hybrid_search_returns_top_k_with_filters(sample_settings):
    engine = HybridSearch(
        settings=sample_settings,
        query_processor=QueryProcessor(),
        dense_retriever=DenseOK(),
        sparse_retriever=SparseOK(),
    )

    results = engine.search("hybrid retrieval", top_k=3, filters={"collection": "spec"})

    assert [r.chunk_id for r in results] == ["b", "a"]


def test_hybrid_search_degrades_when_dense_fails(sample_settings):
    engine = HybridSearch(
        settings=sample_settings,
        query_processor=QueryProcessor(),
        dense_retriever=DenseFail(),
        sparse_retriever=SparseOK(),
    )

    results = engine.search("hybrid retrieval", top_k=2)

    assert [r.chunk_id for r in results] == ["b", "c"]
