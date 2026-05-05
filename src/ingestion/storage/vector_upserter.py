from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from src.core.settings import Settings, get_settings
from src.core.types import Chunk
from src.libs.vector_store.base import BaseVectorStore
from src.libs.vector_store.vector_store_factory import create_vector_store


class VectorUpserter:
    def __init__(self, settings: Optional[Settings] = None, vector_store: Optional[BaseVectorStore] = None):
        self.settings = settings or get_settings()
        self.vector_store = vector_store or create_vector_store(self.settings)

    def upsert(
        self,
        chunks: List[Chunk],
        dense_vectors: Dict[str, List[float]],
        collection: Optional[str] = None,
    ) -> List[str]:
        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[dict] = []
        documents: List[str] = []

        for chunk in chunks:
            vector = dense_vectors.get(chunk.id)
            if vector is None:
                continue

            stable_id = self._stable_id(chunk)
            metadata = dict(chunk.metadata)
            metadata.update({
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "chunk_id": chunk.id,
            })
            if collection:
                metadata["collection"] = collection

            ids.append(stable_id)
            embeddings.append(vector)
            metadatas.append(metadata)
            documents.append(chunk.content)

        if ids:
            self.vector_store.upsert(embeddings=embeddings, metadatas=metadatas, ids=ids, documents=documents)

        return ids

    @staticmethod
    def _stable_id(chunk: Chunk) -> str:
        content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()[:8]
        source = chunk.source or "unknown"
        payload = f"{source}|{chunk.chunk_index}|{content_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
