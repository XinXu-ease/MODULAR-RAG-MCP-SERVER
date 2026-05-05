from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.core.types import EmbeddingConfig, LLMConfig, RetrievalConfig, VectorStoreConfig


@dataclass
class _FallbackSettings:
    _config: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        value: Any = self._config
        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            value = value.get(part)
            if value is None:
                return default
        return value

    @property
    def llm(self) -> LLMConfig:
        cfg = self._config.get("llm", {})
        return LLMConfig(provider=cfg.get("provider", "ollama"), model=cfg.get("model", "llama2"))

    @property
    def embedding(self) -> EmbeddingConfig:
        cfg = self._config.get("embedding", {})
        return EmbeddingConfig(
            provider=cfg.get("provider", "ollama"),
            model=cfg.get("model", "nomic-embed-text"),
            dimension=int(cfg.get("dimension", 384)),
        )

    @property
    def vector_store(self) -> VectorStoreConfig:
        cfg = self._config.get("vector_store", {})
        return VectorStoreConfig(backend=cfg.get("backend", "chroma"), persist_directory=cfg.get("persist_directory", "data/db/chroma"))

    @property
    def retrieval(self) -> RetrievalConfig:
        cfg = self._config.get("retrieval", {})
        return RetrievalConfig(
            top_k=int(cfg.get("top_k", 10)),
            sparse_backend=cfg.get("sparse_backend", "bm25"),
            fusion_algorithm=cfg.get("fusion_algorithm", "rrf"),
            rerank_backend=cfg.get("rerank_backend"),
        )

    @property
    def observability(self) -> Dict[str, Any]:
        return dict(self._config.get("observability", {}))

    @property
    def dashboard(self) -> Dict[str, Any]:
        return dict(self._config.get("dashboard", {}))


def resolve_settings(settings: Optional[Any] = None) -> Any:
    if settings is not None:
        return settings

    try:
        from src.core.settings import get_settings

        return get_settings()
    except Exception:
        return _FallbackSettings(
            {
                "llm": {"provider": "ollama", "model": "llama2"},
                "embedding": {"provider": "ollama", "model": "nomic-embed-text", "dimension": 384},
                "vector_store": {"backend": "chroma", "persist_directory": "data/db/chroma"},
                "retrieval": {"top_k": 10, "sparse_backend": "bm25", "fusion_algorithm": "rrf", "rerank_backend": None},
                "observability": {"enabled": True, "logging": {"log_file": "logs/traces.jsonl", "log_level": "INFO"}},
                "dashboard": {"enabled": True, "port": 8501, "traces_dir": "logs", "auto_refresh": True, "refresh_interval": 5},
                "ingestion": {
                    "bm25_index_dir": "data/db/bm25",
                    "image_root": "data/images",
                    "image_index_db": "data/db/image_index.db",
                    "history_db": "data/db/ingestion_history.db",
                },
            }
        )
