from __future__ import annotations

from typing import Dict, List, Optional

from src.core.settings import Settings, get_settings
from src.core.types import Chunk
from src.libs.embedding.base import BaseEmbedding
from src.libs.embedding.embedding_factory import create_embedding


class DenseEncoder:
    def __init__(self, settings: Optional[Settings] = None, embedding_client: Optional[BaseEmbedding] = None):
        self.settings = settings or get_settings()
        self.embedding_client = embedding_client or create_embedding(self.settings)

    def encode(self, chunks: List[Chunk]) -> Dict[str, List[float]]:
        if not chunks:
            return {}
        vectors = self.embedding_client.embed([chunk.content for chunk in chunks])
        return {chunk.id: vector for chunk, vector in zip(chunks, vectors)}
