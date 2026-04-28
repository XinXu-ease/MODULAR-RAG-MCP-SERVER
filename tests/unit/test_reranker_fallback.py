"""
D6: Reranker 回退机制测试

验证：
- Reranker 正常工作时能改变排序
- 后端异常时能降级回退到原始排名
- metadata 正确标记 fallback 状态
"""

import pytest
from unittest.mock import Mock, patch

from src.core.query_engine.reranker import Reranker
from src.core.types import RetrievalResult
from src.core.settings import Settings


class FakeReranker:
    """假的 Reranker 用于测试正常工作场景."""

    def rerank(self, query, candidates, timeout=10):
        """简单重排：按 text 长度降序排列."""
        return sorted(candidates, key=lambda x: len(x.get("text", "")), reverse=True)


class BrokenReranker:
    """坏的 Reranker，总是抛出异常."""

    def rerank(self, query, candidates, timeout=10):
        raise RuntimeError("Reranker backend failed!")


def test_reranker_normal_operation():
    """测试：Reranker 正常工作时改变排序."""
    settings = Settings()

    # Mock RerankerFactory 返回 FakeReranker
    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = FakeReranker()

        reranker = Reranker(settings)

        # 构造候选结果（不同长度的文本）
        candidates = [
            RetrievalResult(chunk_id="1", text="short", score=0.9, metadata={}),
            RetrievalResult(chunk_id="2", text="very long text here", score=0.7, metadata={}),
            RetrievalResult(chunk_id="3", text="medium", score=0.8, metadata={}),
        ]

        # 执行重排
        reranked = reranker.rerank(query="test", candidates=candidates)

        # 验证：应按文本长度重新排序（长度递减）
        assert len(reranked) == 3
        assert reranked[0].chunk_id == "2"  # "very long text here"
        assert reranked[1].chunk_id == "3"  # "medium"
        assert reranked[2].chunk_id == "1"  # "short"

        # 验证 metadata 标记
        for result in reranked:
            assert result.metadata.get("reranked") is True
            assert result.metadata.get("fallback_reason") is None


def test_reranker_fallback_on_exception():
    """测试：后端异常时回退到原始排名."""
    settings = Settings()

    # Mock RerankerFactory 返回坏的 Reranker
    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = BrokenReranker()

        reranker = Reranker(settings)

        # 构造候选结果
        candidates = [
            RetrievalResult(chunk_id="1", text="first", score=0.9, metadata={}),
            RetrievalResult(chunk_id="2", text="second", score=0.7, metadata={}),
        ]

        original_order = [c.chunk_id for c in candidates]

        # 执行重排（会失败并降级）
        fallback_results = reranker.rerank(query="test", candidates=candidates)

        # 验证：结果顺序保持原样（降级）
        assert len(fallback_results) == 2
        fallback_order = [c.chunk_id for c in fallback_results]
        assert fallback_order == original_order

        # 验证 metadata 标记 fallback
        for result in fallback_results:
            assert result.metadata.get("reranked") is False
            assert result.metadata.get("fallback_reason") is not None
            assert "RuntimeError" in result.metadata.get("fallback_reason", "")


def test_reranker_top_k_limit():
    """测试：Reranker 尊重 top_k 限制."""
    settings = Settings()

    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = FakeReranker()

        reranker = Reranker(settings)

        # 构造大量候选
        candidates = [
            RetrievalResult(chunk_id=str(i), text="x" * (i + 1), score=1.0 - i * 0.1, metadata={})
            for i in range(10)
        ]

        # 只取前3个
        reranked = reranker.rerank(query="test", candidates=candidates, top_k=3)

        assert len(reranked) == 3


def test_reranker_none_backend():
    """测试：backend=none 时不进行重排."""
    settings = Settings()

    # Mock RerankerFactory 返回 None（禁用 Reranker）
    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = None

        reranker = Reranker(settings)

        candidates = [
            RetrievalResult(chunk_id="1", text="first", score=0.9, metadata={}),
            RetrievalResult(chunk_id="2", text="second", score=0.7, metadata={}),
        ]

        # 执行时应直接返回原始顺序
        results = reranker.rerank(query="test", candidates=candidates)

        assert len(results) == 2
        assert results[0].chunk_id == "1"
        assert results[1].chunk_id == "2"


def test_reranker_empty_candidates():
    """测试：空候选列表处理."""
    settings = Settings()

    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = FakeReranker()

        reranker = Reranker(settings)

        # 空候选
        results = reranker.rerank(query="test", candidates=[])

        assert len(results) == 0


def test_reranker_with_trace():
    """测试：Trace 上下文正确记录."""
    settings = Settings()

    with patch("src.core.query_engine.reranker.RerankerFactory.create") as mock_factory:
        mock_factory.return_value = FakeReranker()

        reranker = Reranker(settings)

        candidates = [
            RetrievalResult(chunk_id="1", text="short", score=0.9, metadata={}),
            RetrievalResult(chunk_id="2", text="very long", score=0.7, metadata={}),
        ]

        # Mock trace
        trace = Mock()
        trace.record_stage = Mock()

        reranker.rerank(query="test", candidates=candidates, trace=trace)

        # 验证 trace 被调用
        trace.record_stage.assert_called_once()
        call_args = trace.record_stage.call_args
        assert call_args[1].get("fallback") is False
