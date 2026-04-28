"""
D7: query.py 脚本测试

验证：
- 命令行参数解析正确
- 查询流程能完整执行
- 结果格式化正确
- 异常处理有效
"""

import pytest
from unittest.mock import patch, Mock
from io import StringIO
import sys

from scripts.query import run_query, format_result
from src.core.types import RetrievalResult


def test_format_result_basic():
    """测试：基础结果格式化."""
    result = RetrievalResult(
        chunk_id="chunk_001",
        text="This is a test document with some sample text.",
        score=0.85,
        metadata={"source_path": "test.pdf", "page": 1},
    )

    formatted = format_result(1, result, verbose=False)

    assert "[1]" in formatted
    assert "0.8500" in formatted
    assert "chunk_001" in formatted
    assert "test document" in formatted
    assert "test.pdf" in formatted
    assert "Page: 1" in formatted


def test_format_result_long_text():
    """测试：文本超长时的截断."""
    long_text = "x" * 200

    result = RetrievalResult(chunk_id="1", text=long_text, score=0.9, metadata={})

    formatted = format_result(1, result, verbose=False)

    assert "..." in formatted
    assert len(formatted) < len(long_text) + 50  # 应该被截断


def test_format_result_verbose():
    """测试：Verbose 模式显示完整 metadata."""
    result = RetrievalResult(
        chunk_id="1",
        text="test",
        score=0.9,
        metadata={"source_path": "doc.pdf", "custom_field": "value"},
    )

    formatted = format_result(1, result, verbose=True)

    assert "custom_field" in formatted
    assert "value" in formatted


def test_run_query_success():
    """测试：查询成功执行."""
    # Mock HybridSearch 和 Reranker
    with patch("scripts.query.HybridSearch") as mock_hybrid_class, patch(
        "scripts.query.Reranker"
    ) as mock_reranker_class:

        # 配置 HybridSearch mock
        mock_hybrid = Mock()
        mock_hybrid.search.return_value = [
            RetrievalResult(chunk_id="1", text="result 1", score=0.9, metadata={}),
            RetrievalResult(chunk_id="2", text="result 2", score=0.8, metadata={}),
        ]
        mock_hybrid_class.return_value = mock_hybrid

        # 配置 Reranker mock
        mock_reranker = Mock()

        def mock_rerank(query, candidates, top_k, trace):
            return candidates[:top_k]

        mock_reranker.rerank.side_effect = mock_rerank
        mock_reranker_class.return_value = mock_reranker

        # 执行查询
        results = run_query(query="test query", top_k=2, verbose=False)

        # 验证
        assert len(results) == 2
        assert results[0].chunk_id == "1"
        assert results[1].chunk_id == "2"


def test_run_query_empty_results():
    """测试：无结果返回."""
    with patch("scripts.query.HybridSearch") as mock_hybrid_class, patch(
        "scripts.query.Reranker"
    ) as mock_reranker_class:

        # HybridSearch 返回空
        mock_hybrid = Mock()
        mock_hybrid.search.return_value = []
        mock_hybrid_class.return_value = mock_hybrid

        # Reranker
        mock_reranker_class.return_value = Mock()

        results = run_query(query="nonexistent", top_k=10, verbose=False)

        assert len(results) == 0


def test_run_query_skip_rerank():
    """测试：--no-rerank 时跳过重排."""
    with patch("scripts.query.HybridSearch") as mock_hybrid_class, patch(
        "scripts.query.Reranker"
    ) as mock_reranker_class:

        # HybridSearch 返回结果
        candidates = [
            RetrievalResult(chunk_id=str(i), text=f"result {i}", score=0.9 - i * 0.1, metadata={})
            for i in range(5)
        ]
        mock_hybrid = Mock()
        mock_hybrid.search.return_value = candidates
        mock_hybrid_class.return_value = mock_hybrid

        # Reranker
        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker

        # 执行查询但跳过重排
        results = run_query(query="test", top_k=2, no_rerank=True, verbose=False)

        # 验证：没有调用 reranker.rerank
        mock_reranker.rerank.assert_not_called()

        # 验证：返回原始前 2 个结果
        assert len(results) == 2
        assert results[0].chunk_id == "0"
        assert results[1].chunk_id == "1"


def test_run_query_with_collection():
    """测试：指定 collection 参数."""
    with patch("scripts.query.HybridSearch") as mock_hybrid_class, patch(
        "scripts.query.Reranker"
    ) as mock_reranker_class:

        mock_hybrid = Mock()
        mock_hybrid.search.return_value = []
        mock_hybrid_class.return_value = mock_hybrid

        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker

        run_query(query="test", collection="my_collection", verbose=False)

        # 验证：HybridSearch 初始化时传入了 collection
        check_kwarg = mock_hybrid_class.call_args
        assert check_kwarg[1].get("collection_name") == "my_collection"


def test_run_query_with_trace():
    """测试：Trace 上下文被正确创建."""
    with patch("scripts.query.HybridSearch") as mock_hybrid_class, patch(
        "scripts.query.Reranker"
    ) as mock_reranker_class, patch("scripts.query.TraceContext") as mock_trace_class:

        mock_trace = Mock()
        mock_trace_class.return_value = mock_trace

        mock_hybrid = Mock()
        mock_hybrid.search.return_value = [
            RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})
        ]
        mock_hybrid_class.return_value = mock_hybrid

        mock_reranker = Mock()

        def mock_rerank(query, candidates, top_k, trace):
            assert trace == mock_trace  # 验证 trace 传入
            return candidates[:top_k]

        mock_reranker.rerank.side_effect = mock_rerank
        mock_reranker_class.return_value = mock_reranker

        run_query(query="test", verbose=False)

        # 验证 TraceContext 被创建
        mock_trace_class.assert_called_once()


def test_run_query_exception_handling():
    """测试：异常被正确捕获和报告."""
    with patch("scripts.query.HybridSearch") as mock_hybrid_class:

        # HybridSearch 抛出异常
        mock_hybrid = Mock()
        mock_hybrid.search.side_effect = RuntimeError("Database connection failed")
        mock_hybrid_class.return_value = mock_hybrid

        # 不会抛出异常，但应该处理
        with pytest.raises(RuntimeError):
            run_query(query="test", verbose=False)
