from __future__ import annotations

from typing import List, Optional

from src.core.types import RetrievalResult
from src.libs.embedding.base import BaseEmbedding
from src.libs.embedding.embedding_factory import create_embedding
from src.libs.vector_store.base import BaseVectorStore
from src.libs.vector_store.vector_store_factory import create_vector_store


class DenseRetriever:
    """Dense retrieval backed by the configured embedding model and vector store."""

    def __init__(
        self,
        embedding_model: Optional[BaseEmbedding] = None,
        vector_store: Optional[BaseVectorStore] = None,
    ):
        self.embedding_model = embedding_model or create_embedding()
        self.vector_store = vector_store or create_vector_store()

    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        query = query.strip()
        if not query:
            return []

        query_vector = self.embedding_model.embed([query])[0]
        raw_results = self.vector_store.query(query_vector, top_k=top_k)

        results: List[RetrievalResult] = []
        for item in raw_results:
            score = self._distance_to_score(float(item.get("distance", 1.0)))
            metadata = dict(item.get("metadata") or {})
            results.append(
                RetrievalResult(
                    chunk_id=str(item["id"]),
                    content=item.get("text") or "",
                    metadata=metadata,
                    score=score,
                    score_breakdown={"dense": score},
                    image_refs=list(metadata.get("image_refs", [])),
                )
            )
        return results

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        return max(0.0, min(1.0, 1.0 / (1.0 + max(distance, 0.0))))
