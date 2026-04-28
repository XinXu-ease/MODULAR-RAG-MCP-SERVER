from __future__ import annotations

from typing import Dict, List, Optional

from src.core.types import RetrievalResult


class RRFFusion:
    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        dense_results: Optional[List[RetrievalResult]] = None,
        sparse_results: Optional[List[RetrievalResult]] = None,
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        dense_results = dense_results or []
        sparse_results = sparse_results or []

        merged: Dict[str, RetrievalResult] = {}
        total_scores: Dict[str, float] = {}
        breakdowns: Dict[str, Dict[str, float]] = {}

        self._accumulate("dense", dense_results, merged, total_scores, breakdowns)
        self._accumulate("sparse", sparse_results, merged, total_scores, breakdowns)

        ranked = sorted(total_scores.items(), key=lambda item: item[1], reverse=True)
        out: List[RetrievalResult] = []
        for chunk_id, score in ranked[:top_k]:
            base = merged[chunk_id]
            out.append(
                RetrievalResult(
                    chunk_id=base.chunk_id,
                    content=base.content,
                    metadata=base.metadata,
                    score=score,
                    score_breakdown=breakdowns.get(chunk_id, {}),
                    image_refs=list(base.image_refs),
                )
            )
        return out

    def _accumulate(
        self,
        source: str,
        results: List[RetrievalResult],
        merged: Dict[str, RetrievalResult],
        total_scores: Dict[str, float],
        breakdowns: Dict[str, Dict[str, float]],
    ) -> None:
        for rank, item in enumerate(results):
            if not item.chunk_id:
                continue

            rrf_score = 1.0 / (self.k + rank + 1)
            total_scores[item.chunk_id] = total_scores.get(item.chunk_id, 0.0) + rrf_score
            source_scores = breakdowns.setdefault(item.chunk_id, {})
            source_scores[source] = rrf_score

            existing = merged.get(item.chunk_id)
            if existing is None:
                merged[item.chunk_id] = item
            elif not existing.content and item.content:
                merged[item.chunk_id] = item
