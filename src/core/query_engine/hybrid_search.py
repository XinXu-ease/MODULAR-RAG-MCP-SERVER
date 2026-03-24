from __future__ import annotations

import time
from typing import Dict, List, Optional

from src.core.trace import TraceContext
from src.core.types import QueryResult, RetrievalResult
from src.libs.reranker.base import BaseReranker
from src.libs.reranker.reranker_factory import create_reranker

from .dense_retriever import DenseRetriever
from .sparse_retriever import SparseRetriever


class HybridSearch:
    """Combine dense and sparse retrieval with reciprocal-rank fusion."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        reranker: Optional[BaseReranker] = None,
        rrf_k: int = 60,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.reranker = reranker or create_reranker()
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        use_rerank: bool = True,
        trace: Optional[TraceContext] = None,
    ) -> QueryResult:
        trace = trace or TraceContext(trace_type="query")
        stage_latencies: Dict[str, float] = {}

        dense_results, dense_ms = self._timed_search(self.dense_retriever.search, query, top_k)
        stage_latencies["dense_retrieval"] = dense_ms
        trace.record_stage(
            "dense_retrieval",
            elapsed_ms=dense_ms,
            method="dense",
            candidate_count=len(dense_results),
        )

        sparse_results, sparse_ms = self._timed_search(self.sparse_retriever.search, query, top_k)
        stage_latencies["sparse_retrieval"] = sparse_ms
        trace.record_stage(
            "sparse_retrieval",
            elapsed_ms=sparse_ms,
            method="bm25",
            candidate_count=len(sparse_results),
        )

        fused_start = time.perf_counter()
        fused_results = self._fuse_results(dense_results, sparse_results, top_k)
        fusion_ms = (time.perf_counter() - fused_start) * 1000
        stage_latencies["fusion"] = fusion_ms
        trace.record_stage(
            "fusion",
            elapsed_ms=fusion_ms,
            method="rrf",
            candidate_count=len(fused_results),
        )

        rerank_method = None
        if use_rerank and fused_results:
            rerank_start = time.perf_counter()
            reranked = self.reranker.rerank(query, [self._to_candidate(item) for item in fused_results])
            rerank_ms = (time.perf_counter() - rerank_start) * 1000
            stage_latencies["rerank"] = rerank_ms
            trace.record_stage(
                "rerank",
                elapsed_ms=rerank_ms,
                method=self.reranker.__class__.__name__.lower(),
                candidate_count=len(reranked),
            )
            fused_results = self._apply_rerank(fused_results, reranked)
            rerank_method = self.reranker.__class__.__name__

        trace.finish()
        return QueryResult(
            query=query,
            retrieved_chunks=fused_results[:top_k],
            total_latency_ms=trace.total_latency_ms,
            stage_latencies=stage_latencies,
            trace_id=trace.trace_id,
            retrieval_method="hybrid",
            rerank_method=rerank_method,
        )

    def _fuse_results(
        self,
        dense_results: List[RetrievalResult],
        sparse_results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        fused: Dict[str, RetrievalResult] = {}

        for name, results in (("dense", dense_results), ("sparse", sparse_results)):
            for rank, item in enumerate(results):
                fused_score = 1.0 / float(self.rrf_k + rank + 1)
                existing = fused.get(item.chunk_id)
                if existing is None:
                    score_breakdown = dict(item.score_breakdown or {})
                    score_breakdown["fusion"] = fused_score
                    fused[item.chunk_id] = RetrievalResult(
                        chunk_id=item.chunk_id,
                        content=item.content,
                        metadata=dict(item.metadata),
                        score=fused_score,
                        score_breakdown=score_breakdown,
                        image_refs=list(item.image_refs),
                    )
                    continue

                existing.score += fused_score
                breakdown = dict(existing.score_breakdown or {})
                breakdown[name] = item.score
                breakdown["fusion"] = existing.score
                existing.score_breakdown = breakdown

        ranked = sorted(fused.values(), key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _to_candidate(item: RetrievalResult) -> Dict[str, object]:
        return {
            "chunk_id": item.chunk_id,
            "content": item.content,
            "metadata": item.metadata,
            "score": item.score,
            "score_breakdown": dict(item.score_breakdown or {}),
            "image_refs": list(item.image_refs),
        }

    @staticmethod
    def _apply_rerank(
        original: List[RetrievalResult],
        reranked: List[Dict[str, object]],
    ) -> List[RetrievalResult]:
        by_id = {item.chunk_id: item for item in original}
        results: List[RetrievalResult] = []
        for rank, candidate in enumerate(reranked):
            chunk_id = str(candidate.get("chunk_id"))
            source = by_id.get(chunk_id)
            if source is None:
                continue
            score = 1.0 / float(rank + 1)
            breakdown = dict(source.score_breakdown or {})
            breakdown["rerank"] = score
            results.append(
                RetrievalResult(
                    chunk_id=source.chunk_id,
                    content=source.content,
                    metadata=dict(source.metadata),
                    score=score,
                    score_breakdown=breakdown,
                    image_refs=list(source.image_refs),
                )
            )
        return results

    @staticmethod
    def _timed_search(fn, query: str, top_k: int):
        start = time.perf_counter()
        results = fn(query, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return results, elapsed_ms
