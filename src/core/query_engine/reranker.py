"""Core Reranker 编排层：整合 libs.reranker 后端，失败/超时回退 fusion 排名."""

from typing import Any, Dict, List, Optional

from src.core.settings import Settings, get_settings
from src.core.types import RetrievalResult
from src.libs.reranker.reranker_factory import create_reranker


class Reranker:
    """
    Reranker 编排层：
    - 接入 libs.reranker 后端（CrossEncoder / LLM / None）
    - 支持失败/超时回退到原始排名
    - 满足 D6 需求：降级不阻塞，标记 fallback 状态
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化 Reranker。

        Args:
            settings: 系统配置对象，用于读取 rerank 后端配置
        """
        self.settings = settings or get_settings()
        self.backend_reranker = create_reranker(self.settings)

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: Optional[int] = None,
        trace: Optional[Any] = None,
        timeout_seconds: float = 10.0,
    ) -> List[RetrievalResult]:
        """
        对候选结果进行重排序，支持失败降级。

        Args:
            query: 原始查询字符串
            candidates: 从 HybridSearch 融合得到的候选结果列表
            top_k: 最终返回数量（若不指定则返回全部候选）
            trace: 追踪上下文，用于记录中间状态
            timeout_seconds: Reranker 后端的超时控制（秒）

        Returns:
            重排后的 Top-K 结果列表；若后端失败则返回原始候选（降级）

        Behavior:
            - 若后端为 None（disabled），直接返回原始候选
            - 若后端可用，尝试重排；失败则回退并标记 fallback=True
            - 在 metadata 中记录是否进行了重排（reranked: bool）和是否降级（fallback_reason: str | None）
        """
        if not candidates:
            return []

        # 若 Reranker 后端为 None，直接返回原始排序
        if self.backend_reranker is None or (
            hasattr(self.backend_reranker, "__class__")
            and self.backend_reranker.__class__.__name__ == "NoneReranker"
        ):
            if trace is not None:
                trace.record_stage("reranking", backend="none", result_count=len(candidates[:top_k]))
            return candidates[:top_k] if top_k else candidates

        try:
            # 调用后端 Reranker 进行重排
            candidate_dicts = [
                {
                    "id": c.chunk_id,
                    "text": c.text,
                    "score": c.score,
                    "metadata": c.metadata,
                }
                for c in candidates
            ]

            reranked_dicts = self.backend_reranker.rerank(query, candidate_dicts, timeout=timeout_seconds)

            # 重排后的结果映射回 RetrievalResult
            reranked_results: List[RetrievalResult] = []
            for item in reranked_dicts:
                result = RetrievalResult(
                    chunk_id=item.get("id", ""),
                    text=item.get("text", ""),
                    score=item.get("score", 0.0),
                    metadata={**(item.get("metadata") or {}), "reranked": True, "fallback_reason": None},
                )
                reranked_results.append(result)

            if trace is not None:
                trace.record_stage(
                    "reranking",
                    backend=getattr(self.backend_reranker, "__class__").__name__,
                    result_count=len(reranked_results[:top_k]) if top_k else len(reranked_results),
                    fallback=False,
                )

            return reranked_results[:top_k] if top_k else reranked_results

        except Exception as exc:
            # 失败降级：返回原始候选并标记 fallback
            fallback_reason = f"{exc.__class__.__name__}: {str(exc)[:100]}"

            fallback_results: List[RetrievalResult] = []
            for c in candidates:
                # 复制原始 metadata，添加 fallback 标记
                updated_metadata = {**(c.metadata or {}), "reranked": False, "fallback_reason": fallback_reason}
                result = RetrievalResult(
                    chunk_id=c.chunk_id, text=c.text, score=c.score, metadata=updated_metadata
                )
                fallback_results.append(result)

            if trace is not None:
                trace.record_stage(
                    "reranking",
                    backend=getattr(self.backend_reranker, "__class__").__name__,
                    result_count=len(fallback_results[:top_k]) if top_k else len(fallback_results),
                    fallback=True,
                    fallback_reason=fallback_reason,
                )

            return fallback_results[:top_k] if top_k else fallback_results
