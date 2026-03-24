from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional


class BaseVectorStore(ABC):
    """Abstract interface for vector database backends."""

    @abstractmethod
    def add(
        self,
        embeddings: Iterable[List[float]],
        metadatas: Iterable[Dict[str, Any]],
        ids: Optional[Iterable[str]] = None,
        documents: Optional[Iterable[str]] = None,
    ):
        """Append records to the store."""
        raise NotImplementedError

    @abstractmethod
    def upsert(
        self,
        embeddings: Iterable[List[float]],
        metadatas: Iterable[Dict[str, Any]],
        ids: Iterable[str],
        documents: Optional[Iterable[str]] = None,
    ):
        """Insert-or-update records in an idempotent way."""
        raise NotImplementedError

    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """Nearest-neighbor lookup for a query embedding."""
        raise NotImplementedError

    @abstractmethod
    def get_by_ids(self, ids: Iterable[str]) -> List[Dict[str, Any]]:
        """Fetch stored records by ids."""
        raise NotImplementedError
