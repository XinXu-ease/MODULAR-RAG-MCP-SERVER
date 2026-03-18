from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseVectorStore
from .chroma_store import ChromaStore

_PROVIDER_MAP = {
    "chroma": ChromaStore,
}


def create_vector_store(settings: Optional[Settings] = None) -> BaseVectorStore:
    if settings is None:
        settings = get_settings()

    vs_cfg = settings.vector_store
    provider = (vs_cfg.backend or "").lower()
    cls = _PROVIDER_MAP.get(provider)
    if cls is None:
        raise ValueError(f"Unsupported vector store backend: {provider}")
    return cls(persist_directory=vs_cfg.persist_directory)
