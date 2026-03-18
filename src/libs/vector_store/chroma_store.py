from typing import Any, Dict, Iterable, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from .base import BaseVectorStore


class ChromaStore(BaseVectorStore):
    def __init__(self, persist_directory: Optional[str] = None):
        # create or connect to local chroma instance
        settings = {}
        if persist_directory:
            settings["persist_directory"] = persist_directory
        self._client = chromadb.Client(ChromaSettings(**settings))
        self._collection = self._client.get_or_create_collection(name="default")

    def add(self, embeddings: Iterable[List[float]], metadatas: Iterable[Dict[str, Any]], ids: Optional[Iterable[str]] = None):
        self._collection.add(
            embeddings=list(embeddings),
            metadatas=list(metadatas),
            ids=list(ids) if ids is not None else None,
        )

    def query(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        resp = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        results = []
        for i in range(len(resp["ids"][0])):
            results.append({
                "id": resp["ids"][0][i],
                "distance": resp["distances"][0][i],
                "metadata": resp["metadatas"][0][i],
            })
        return results
