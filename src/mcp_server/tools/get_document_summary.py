"""MCP Tool: get_document_summary."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.core.settings import get_settings
from src.libs.vector_store.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class GetDocumentSummaryTool:
    """Resolve a source_ref or chunk_id to document-level summary context."""

    DEFAULT_CONTEXT_WINDOW = 10
    GROUP_KEYS = ("source_ref", "source_hash", "source")
    LOOKUP_KEYS = ("chunk_id", "source_ref", "source_hash", "source")

    def __init__(self, vector_store: Optional[ChromaStore] = None):
        self.vector_store = vector_store or ChromaStore()
        self.settings = get_settings()

    def execute(
        self,
        doc_id: Optional[str] = None,
        *,
        source_ref: Optional[str] = None,
        chunk_id: Optional[str] = None,
        collection: Optional[str] = None,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Return document summary plus a bounded same-source chunk window.

        The historical parameter name is ``doc_id`` for compatibility. In
        practice callers may pass a citation ``source_ref`` or ``chunk_id``.
        """
        lookup_id = self._first_non_empty(source_ref, chunk_id, doc_id)
        if not lookup_id:
            return self._error_response("source_ref, chunk_id, or doc_id cannot be empty")

        try:
            context_window = max(0, int(context_window))
        except (TypeError, ValueError):
            return self._error_response("context_window must be an integer")

        try:
            logger.info(
                "Getting document summary for lookup_id='%s', collection='%s'",
                lookup_id,
                collection,
            )
            document = self._get_document(
                lookup_id=lookup_id,
                collection=collection,
                context_window=context_window,
            )
            if not document:
                return self._error_response(f"Document '{lookup_id}' not found")

            return {
                "success": True,
                "lookup_id": lookup_id,
                "doc_id": document["id"],
                "document": document,
            }
        except Exception as e:
            logger.exception("Failed to get document summary: %s", e)
            return self._error_response(f"Internal error: {str(e)}")

    def _get_document(
        self,
        *,
        lookup_id: str,
        collection: Optional[str],
        context_window: int,
    ) -> Optional[Dict[str, Any]]:
        records = self._fetch_records(lookup_id, collection)
        if not records:
            return None

        anchor = self._find_anchor(records, lookup_id)
        if not anchor:
            return None

        group = self._same_source_group(records, anchor)
        if not group:
            return None

        group.sort(key=self._chunk_sort_key)
        anchor_index = self._index_of_record(group, anchor)
        window_records, start, end = self._window_records(group, anchor_index, context_window)

        anchor_metadata = dict(anchor.get("metadata") or {})
        first_metadata = dict(group[0].get("metadata") or {})
        metadata = {**first_metadata, **anchor_metadata}
        source = str(metadata.get("source") or metadata.get("source_path") or anchor.get("vector_id") or lookup_id)
        title = str(metadata.get("title") or Path(source).stem or source)

        return {
            "id": str(metadata.get("source_ref") or metadata.get("source_hash") or source or lookup_id),
            "lookup_id": lookup_id,
            "source_ref": self._string_or_none(metadata.get("source_ref")),
            "source_hash": self._string_or_none(metadata.get("source_hash")),
            "source": source,
            "title": title,
            "summary": self._summary_text(metadata, group),
            "tags": self._normalize_tags(metadata.get("tags")),
            "doc_type": str(metadata.get("doc_type") or metadata.get("source_type") or "unknown"),
            "collection": str(metadata.get("collection") or collection or self._default_collection_name()),
            "chunk_count": len(group),
            "returned_chunk_count": len(window_records),
            "context_window": context_window,
            "chunk_window": {
                "start_index": start,
                "end_index": end,
                "total_chunks": len(group),
            },
            "anchor": {
                "vector_id": str(anchor.get("vector_id") or ""),
                "chunk_id": str(anchor_metadata.get("chunk_id") or anchor.get("vector_id") or ""),
                "chunk_index": self._safe_int(anchor_metadata.get("chunk_index"), 0),
            },
            "chunks": [self._record_to_chunk(record) for record in window_records],
            "metadata": metadata,
        }

    def _fetch_records(self, lookup_id: str, collection: Optional[str]) -> List[Dict[str, Any]]:
        records = self._records_from_list_records(collection)
        if records:
            return records

        records = self._records_from_collection(collection)
        if records:
            return records

        return self._records_from_get_by_ids(lookup_id, collection)

    def _records_from_list_records(self, collection: Optional[str]) -> List[Dict[str, Any]]:
        list_records = getattr(self.vector_store, "list_records", None)
        if not callable(list_records):
            return []
        try:
            raw_records = list(list_records())
        except Exception:
            return []
        return self._normalize_records(raw_records, collection)

    def _records_from_collection(self, collection: Optional[str]) -> List[Dict[str, Any]]:
        collection_obj = getattr(self.vector_store, "_collection", None)
        get_records = getattr(collection_obj, "get", None)
        if not callable(get_records):
            return []

        try:
            response = get_records(include=["metadatas", "documents"])
        except TypeError:
            try:
                response = get_records()
            except Exception:
                return []
        except Exception:
            return []

        if not isinstance(response, dict):
            return []

        ids = list(response.get("ids") or [])
        metadatas = list(response.get("metadatas") or [])
        documents = list(response.get("documents") or [])
        raw_records: List[Dict[str, Any]] = []
        for index, vector_id in enumerate(ids):
            raw_records.append(
                {
                    "id": vector_id,
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "text": documents[index] if index < len(documents) else "",
                }
            )
        return self._normalize_records(raw_records, collection)

    def _records_from_get_by_ids(self, lookup_id: str, collection: Optional[str]) -> List[Dict[str, Any]]:
        get_by_ids = getattr(self.vector_store, "get_by_ids", None)
        if not callable(get_by_ids):
            return []
        try:
            raw_records = list(get_by_ids([lookup_id]) or [])
        except Exception:
            return []
        return self._normalize_records(raw_records, collection)

    def _normalize_records(
        self,
        records: Iterable[Dict[str, Any]],
        collection: Optional[str],
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            metadata = dict(record.get("metadata") or {})
            item = {
                "vector_id": str(record.get("vector_id") or record.get("id") or ""),
                "metadata": metadata,
                "content": str(record.get("content") or record.get("text") or ""),
            }
            if self._matches_collection(item, collection):
                normalized.append(item)
        return normalized

    @staticmethod
    def _matches_collection(record: Dict[str, Any], collection: Optional[str]) -> bool:
        if collection is None:
            return True
        metadata = record.get("metadata", {})
        return str(metadata.get("collection", "default")) == str(collection)

    def _find_anchor(self, records: List[Dict[str, Any]], lookup_id: str) -> Optional[Dict[str, Any]]:
        lookup_id = str(lookup_id)

        for record in records:
            if str(record.get("vector_id")) == lookup_id:
                return record

        for record in records:
            metadata = record.get("metadata", {})
            for key in self.LOOKUP_KEYS:
                if self._metadata_matches(metadata, key, lookup_id):
                    return record

        return None

    def _same_source_group(
        self,
        records: List[Dict[str, Any]],
        anchor: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        anchor_metadata = anchor.get("metadata", {})
        key, value = self._group_key(anchor, anchor_metadata)
        if not value:
            return [anchor]

        group: List[Dict[str, Any]] = []
        for record in records:
            metadata = record.get("metadata", {})
            candidate = metadata.get(key) if key else record.get("vector_id")
            if str(candidate) == value:
                group.append(record)
        return group or [anchor]

    def _group_key(self, record: Dict[str, Any], metadata: Dict[str, Any]) -> Tuple[Optional[str], str]:
        for key in self.GROUP_KEYS:
            value = metadata.get(key)
            if value:
                return key, str(value)
        return None, str(record.get("vector_id") or "")

    @staticmethod
    def _metadata_matches(metadata: Dict[str, Any], key: str, lookup_id: str) -> bool:
        value = metadata.get(key)
        if isinstance(value, list):
            return lookup_id in {str(item) for item in value}
        return str(value) == lookup_id if value is not None else False

    @classmethod
    def _chunk_sort_key(cls, record: Dict[str, Any]) -> Tuple[int, str]:
        metadata = record.get("metadata", {})
        return cls._safe_int(metadata.get("chunk_index"), 0), str(record.get("vector_id") or "")

    @staticmethod
    def _index_of_record(records: List[Dict[str, Any]], target: Dict[str, Any]) -> int:
        target_id = str(target.get("vector_id") or "")
        for index, record in enumerate(records):
            if str(record.get("vector_id") or "") == target_id:
                return index
        return 0

    @staticmethod
    def _window_records(
        records: List[Dict[str, Any]],
        anchor_index: int,
        context_window: int,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        start = max(0, anchor_index - context_window)
        end = min(len(records), anchor_index + context_window + 1)
        return records[start:end], start, end - 1

    def _record_to_chunk(self, record: Dict[str, Any]) -> Dict[str, Any]:
        metadata = dict(record.get("metadata") or {})
        return {
            "vector_id": str(record.get("vector_id") or ""),
            "chunk_id": str(metadata.get("chunk_id") or record.get("vector_id") or ""),
            "chunk_index": self._safe_int(metadata.get("chunk_index"), 0),
            "title": metadata.get("title"),
            "source_ref": self._string_or_none(metadata.get("source_ref")),
            "source": metadata.get("source"),
            "page": metadata.get("page"),
            "content": str(record.get("content") or ""),
            "metadata": metadata,
        }

    @staticmethod
    def _summary_text(metadata: Dict[str, Any], group: List[Dict[str, Any]]) -> str:
        summary = metadata.get("summary")
        if summary:
            return str(summary)

        preview_parts = [str(record.get("content") or "").strip() for record in group[:3]]
        preview = " ".join(part for part in preview_parts if part)
        if preview:
            return preview[:600]
        return "No summary available"

    @staticmethod
    def _normalize_tags(tags: Any) -> List[str]:
        if isinstance(tags, list):
            return [str(item) for item in tags]
        if isinstance(tags, str):
            return [item.strip() for item in tags.split(",") if item.strip()]
        return []

    def _default_collection_name(self) -> str:
        return str(self.settings.get("dashboard.collection", "default"))

    @staticmethod
    def _first_non_empty(*values: Optional[str]) -> Optional[str]:
        for value in values:
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _string_or_none(value: Any) -> Optional[str]:
        return str(value) if value else None

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def to_tool_schema() -> Dict[str, Any]:
        return {
            "name": "get_document_summary",
            "description": (
                "Resolve a citation source_ref or chunk_id to document-level "
                "summary metadata and a bounded same-source chunk window."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": (
                            "Backward-compatible lookup ID. May be a source_ref, "
                            "chunk_id, source_hash, source path/URL, or vector ID."
                        ),
                    },
                    "source_ref": {
                        "type": "string",
                        "description": "Original loaded document reference from a citation.",
                    },
                    "chunk_id": {
                        "type": "string",
                        "description": "Exact retrieved chunk ID from a citation.",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Optional collection namespace filter.",
                    },
                    "context_window": {
                        "type": "integer",
                        "description": "Number of neighboring chunks to return on each side. Default: 10.",
                        "default": GetDocumentSummaryTool.DEFAULT_CONTEXT_WINDOW,
                    },
                },
                "required": [],
            },
        }

    @staticmethod
    def _error_response(error_msg: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": error_msg,
        }


async def get_document_summary(
    doc_id: Optional[str] = None,
    *,
    source_ref: Optional[str] = None,
    chunk_id: Optional[str] = None,
    collection: Optional[str] = None,
    context_window: int = GetDocumentSummaryTool.DEFAULT_CONTEXT_WINDOW,
) -> Dict[str, Any]:
    """Standalone function for MCP integration."""
    tool = GetDocumentSummaryTool()
    return tool.execute(
        doc_id=doc_id,
        source_ref=source_ref,
        chunk_id=chunk_id,
        collection=collection,
        context_window=context_window,
    )
