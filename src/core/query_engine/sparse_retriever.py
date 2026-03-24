from __future__ import annotations

from typing import Dict, List, Optional

from src.core.types import RetrievalResult
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.libs.vector_store.base import BaseVectorStore
from src.libs.vector_store.vector_store_factory import create_vector_store


class SparseRetriever:
    """Sparse retrieval backed by the persisted BM25 index."""

    def __init__(
        self,
        bm25_indexer: Optional[BM25Indexer] = None,
        vector_store: Optional[BaseVectorStore] = None,
    ):
        self.bm25_indexer = bm25_indexer or BM25Indexer()
        self.bm25_indexer.load()
        self.vector_store = vector_store or create_vector_store()

    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        query = query.strip()
        if not query:
            return []

        ranked_ids = self.bm25_indexer.query(query, top_k=top_k)
        if not ranked_ids:
            return []

        id_to_rank: Dict[str, int] = {chunk_id: idx for idx, chunk_id in enumerate(ranked_ids)}
        stored_records = self.vector_store.get_by_ids(ranked_ids)

        results: List[RetrievalResult] = []
        for item in stored_records:
            chunk_id = str(item["id"])
            rank = id_to_rank.get(chunk_id, len(ranked_ids))
            score = self._rank_to_score(rank)
            metadata = dict(item.get("metadata") or {})
            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    content=item.get("text") or "",
                    metadata=metadata,
                    score=score,
                    score_breakdown={"sparse": score},
                    image_refs=list(metadata.get("image_refs", [])),
                )
            )

        results.sort(key=lambda item: id_to_rank.get(item.chunk_id, len(ranked_ids)))
        return results

    @staticmethod
    def _rank_to_score(rank: int) -> float:
        return 1.0 / float(rank + 1)
