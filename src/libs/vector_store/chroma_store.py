from typing import Any, Dict, Iterable, List, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:  # pragma: no cover
    chromadb = None
    ChromaSettings = None

from .base import BaseVectorStore


class ChromaStore(BaseVectorStore):
    def __init__(self, persist_directory: Optional[str] = None):
        if chromadb is None or ChromaSettings is None:
            raise RuntimeError("chromadb package is required for ChromaStore. Install: pip install chromadb")

        settings = {}
        if persist_directory:
            settings["persist_directory"] = persist_directory
        self._client = chromadb.Client(ChromaSettings(**settings))
        self._collection = self._client.get_or_create_collection(name="default")

    def add(
        self,
        embeddings: Iterable[List[float]],
        metadatas: Iterable[Dict[str, Any]],
        ids: Optional[Iterable[str]] = None,
        documents: Optional[Iterable[str]] = None,
    ):
        kwargs: Dict[str, Any] = {
            "embeddings": list(embeddings),
            "metadatas": list(metadatas),
        }
        if ids is not None:
            kwargs["ids"] = list(ids)
        if documents is not None:
            kwargs["documents"] = list(documents)
        self._collection.add(**kwargs)

    def upsert(
        self,
        embeddings: Iterable[List[float]],
        metadatas: Iterable[Dict[str, Any]],
        ids: Iterable[str],
        documents: Optional[Iterable[str]] = None,
    ):
        kwargs: Dict[str, Any] = {
            "embeddings": list(embeddings),
            "metadatas": list(metadatas),
            "ids": list(ids),
        }
        if documents is not None:
            kwargs["documents"] = list(documents)
        self._collection.upsert(**kwargs)

    def query(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        resp = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "distances", "documents"],
        )
        results = []
        for i in range(len(resp["ids"][0])):
            results.append(
                {
                    "id": resp["ids"][0][i],
                    "distance": resp["distances"][0][i],
                    "metadata": resp["metadatas"][0][i],
                    "text": resp.get("documents", [[None]])[0][i],
                }
            )
        return results
