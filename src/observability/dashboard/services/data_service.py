from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from src.core.settings import Settings
from src.ingestion.document_manager import DocumentManager

from ._compat import resolve_settings
from .trace_service import TraceService


class DataService:
    """High-level dashboard data access facade."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        document_manager: Optional[DocumentManager] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.settings = resolve_settings(settings)
        self.document_manager = document_manager or DocumentManager(self.settings)
        self.trace_service = trace_service or TraceService(
            self.settings.get("observability.logging.log_file", "logs/traces.jsonl")
        )

    def get_overview(self) -> Dict[str, Any]:
        stats = self.document_manager.get_collection_stats()
        trace_summary = self.trace_service.summarize()
        return {
            "stats": stats.to_dict(),
            "trace_summary": trace_summary,
            "collections": self.document_manager.list_collections(),
        }

    def list_documents(self, collection: Optional[str] = None) -> List[Dict[str, Any]]:
        return [summary.to_dict() for summary in self.document_manager.list_documents(collection)]

    def get_document_detail(self, doc_id: str, collection: Optional[str] = None) -> Dict[str, Any]:
        return self.document_manager.get_document_detail(doc_id, collection).to_dict()

    def delete_document(self, source: str, collection: Optional[str] = None) -> Dict[str, Any]:
        return self.document_manager.delete_document(source, collection).to_dict()

    def list_images(self, collection: Optional[str] = None, doc_hash: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.document_manager.image_storage.list_images(collection=collection, doc_hash=doc_hash)
