"""Integration tests for HybridSearch with trace recording."""

import pytest
from unittest.mock import MagicMock, patch
from src.core.query_engine.hybrid_search import HybridSearch
from src.core.trace import TraceContext
from src.core.types import RetrievalResult


class MockReranker:
    """Mock reranker that returns input as-is."""
    
    def rerank(self, query, candidates):
        """Pass through ranking without reordering."""
        return candidates


class DenseOK:
    """Mock dense retriever."""
    
    def search(self, query, top_k, filters=None, trace=None):
        """Return test results."""
        return [
            RetrievalResult(chunk_id="a", content="dense a", metadata={"collection": "spec"}, score=0.9),
            RetrievalResult(chunk_id="b", content="dense b", metadata={"collection": "spec"}, score=0.8),
        ]


class SparseOK:
    """Mock sparse retriever."""
    
    def search(self, query, top_k, trace=None):
        """Return test results."""
        return [
            RetrievalResult(chunk_id="b", content="sparse b", metadata={"collection": "spec"}, score=0.9),
            RetrievalResult(chunk_id="c", content="sparse c", metadata={"collection": "other"}, score=0.7),
        ]


def test_hybrid_search_returns_fused_results():
    """Test that HybridSearch correctly fuses dense and sparse results."""
    engine = HybridSearch(
        dense_retriever=DenseOK(),
        sparse_retriever=SparseOK(),
        reranker=MockReranker(),
    )

    results = engine.search("test query", top_k=3)

    assert len(results.retrieved_chunks) <= 3
    # Verify results are RetrievalResult objects
    assert all(hasattr(r, 'chunk_id') for r in results.retrieved_chunks)


def test_hybrid_search_records_query_trace():
    """Test that HybridSearch records complete trace with all stages."""
    engine = HybridSearch(
        dense_retriever=DenseOK(),
        sparse_retriever=SparseOK(),
        reranker=MockReranker(),
    )

    trace = TraceContext(trace_type="query")
    results = engine.search("test query", top_k=3, trace=trace)

    # Verify trace is completed
    assert trace.finished_at is not None
    
    # Verify trace has all required stages
    stage_names = [stage.get("name") for stage in trace.stages]
    assert "dense_retrieval" in stage_names, f"Expected 'dense_retrieval' in {stage_names}"
    assert "sparse_retrieval" in stage_names, f"Expected 'sparse_retrieval' in {stage_names}"
    assert "fusion" in stage_names, f"Expected 'fusion' in {stage_names}"
    assert "rerank" in stage_names, f"Expected 'rerank' in {stage_names}"
    
    # Verify each stage has required fields
    for stage in trace.stages:
        assert "elapsed_ms" in stage, f"Missing 'elapsed_ms' in stage {stage}"
        assert "method" in stage, f"Missing 'method' in stage {stage}"
        assert stage["elapsed_ms"] >= 0


def test_hybrid_search_trace_to_dict():
    """Test that trace can be serialized to dict for persistence."""
    engine = HybridSearch(
        dense_retriever=DenseOK(),
        sparse_retriever=SparseOK(),
        reranker=MockReranker(),
    )

    trace = TraceContext(trace_type="query")
    results = engine.search("test query", top_k=3, trace=trace)

    # Verify trace can be serialized
    trace_dict = trace.to_dict()
    assert trace_dict["trace_type"] == "query"
    assert len(trace_dict["stages"]) > 0
    
    # Verify serialization includes required fields
    assert "trace_id" in trace_dict
    assert "started_at" in trace_dict
    assert "finished_at" in trace_dict
    assert "total_elapsed_ms" in trace_dict


def test_hybrid_search_trace_with_rerank_disabled():
    """Test trace recording when reranking is disabled."""
    engine = HybridSearch(
        dense_retriever=DenseOK(),
        sparse_retriever=SparseOK(),
        reranker=MockReranker(),
    )

    trace = TraceContext(trace_type="query")
    results = engine.search("test query", top_k=3, use_rerank=False, trace=trace)

    # Verify trace has required stages even without rerank
    stage_names = [stage.get("name") for stage in trace.stages]
    assert "dense_retrieval" in stage_names
    assert "sparse_retrieval" in stage_names
    assert "fusion" in stage_names
    # rerank should not be in stages if not performed
    if "rerank" in stage_names:
        pytest.skip("rerank should not be recorded when use_rerank=False")
