from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.settings import Settings

from ._compat import resolve_settings


class ConfigService:
    """Expose dashboard-friendly views of Settings."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = resolve_settings(settings)

    def get_dashboard_config(self) -> Dict[str, Any]:
        return dict(self.settings.dashboard)

    def get_observability_config(self) -> Dict[str, Any]:
        return dict(self.settings.observability)

    def get_component_snapshot(self) -> Dict[str, Any]:
        return {
            "llm": {
                "provider": self.settings.llm.provider,
                "model": self.settings.llm.model,
            },
            "embedding": {
                "provider": self.settings.embedding.provider,
                "model": self.settings.embedding.model,
                "dimension": self.settings.embedding.dimension,
            },
            "vector_store": {
                "backend": self.settings.vector_store.backend,
                "persist_directory": self.settings.vector_store.persist_directory,
            },
            "retrieval": {
                "top_k": self.settings.retrieval.top_k,
                "sparse_backend": self.settings.retrieval.sparse_backend,
                "fusion_algorithm": self.settings.retrieval.fusion_algorithm,
                "rerank_backend": self.settings.retrieval.rerank_backend,
            },
        }
