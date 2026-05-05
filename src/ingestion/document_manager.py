from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.core.settings import Settings
from src.libs.vector_store.base import BaseVectorStore
from src.libs.vector_store.vector_store_factory import create_vector_store
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.ingestion.storage.image_storage import ImageStorage
from src.observability.dashboard.services._compat import resolve_settings


@dataclass
class DocumentChunkDetail:
    vector_id: str
    chunk_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    image_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentSummary:
    doc_id: str
    source: str
    title: str
    collection: str
    doc_type: str
    chunk_count: int
    image_count: int
    last_modified: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentDetail(DocumentSummary):
    chunks: List[DocumentChunkDetail] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["chunks"] = [chunk.to_dict() for chunk in self.chunks]
        return payload


@dataclass
class CollectionStats:
    collection: str
    document_count: int
    chunk_count: int
    image_count: int
    doc_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeleteResult:
    success: bool
    source: str
    collection: str
    removed_vectors: int = 0
    removed_chunks: int = 0
    removed_images: int = 0
    removed_history_rows: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentManager:
    """Coordinate document listing, detail lookup, and deletion across storage backends."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        vector_store: Optional[BaseVectorStore] = None,
        bm25_indexer: Optional[BM25Indexer] = None,
        image_storage: Optional[ImageStorage] = None,
        history_db_path: Optional[str] = None,
    ):
        self.settings = resolve_settings(settings)
        self.vector_store = vector_store or create_vector_store(self.settings)
        self.bm25_indexer = bm25_indexer or BM25Indexer(
            index_dir=self.settings.get("ingestion.bm25_index_dir", "data/db/bm25")
        )
        self.image_storage = image_storage or ImageStorage(
            image_root=self.settings.get("ingestion.image_root", "data/images"),
            db_path=self.settings.get("ingestion.image_index_db", "data/db/image_index.db"),
        )
        self.history_db_path = Path(
            history_db_path or self.settings.get("ingestion.history_db", "data/db/ingestion_history.db")
        )

    def list_documents(self, collection: Optional[str] = None) -> List[DocumentSummary]:
        groups = self._group_records(self._fetch_records(collection))
        return [self._build_summary(group, collection) for group in groups.values()]

    def get_document_detail(self, doc_id: str, collection: Optional[str] = None) -> DocumentDetail:
        records = self._fetch_records(collection)
        group = self._find_group(records, doc_id, collection)
        if not group:
            raise LookupError(f"Document not found: {doc_id}")
        summary = self._build_summary(group, collection)
        chunks = [self._record_to_chunk(record) for record in group]
        chunks.sort(key=lambda item: item.chunk_index)
        return DocumentDetail(**summary.to_dict(), chunks=chunks)

    def get_collection_stats(self, collection: Optional[str] = None) -> CollectionStats:
        summaries = self.list_documents(collection)
        doc_types: Dict[str, int] = {}
        chunk_count = 0
        image_count = 0
        for summary in summaries:
            chunk_count += summary.chunk_count
            image_count += summary.image_count
            doc_types[summary.doc_type] = doc_types.get(summary.doc_type, 0) + 1
        return CollectionStats(
            collection=collection or self._default_collection_name(),
            document_count=len(summaries),
            chunk_count=chunk_count,
            image_count=image_count,
            doc_types=doc_types,
        )

    def delete_document(self, source: str, collection: Optional[str] = None) -> DeleteResult:
        records = self._fetch_records(collection)
        group = self._find_group(records, source, collection)
        if not group:
            return DeleteResult(
                success=False,
                source=source,
                collection=collection or self._default_collection_name(),
                message="document not found",
            )

        summary = self._build_summary(group, collection)
        vector_ids = [record["vector_id"] for record in group]
        chunk_ids = [record["metadata"].get("chunk_id", record["vector_id"]) for record in group]
        source_hash = group[0]["metadata"].get("source_hash")

        removed_vectors = self._delete_from_vector_store(vector_ids, summary)
        removed_chunks = self._remove_from_bm25(chunk_ids)
        removed_images = self._remove_images(source_hash, collection or summary.collection)
        removed_history_rows = self._remove_history_rows(summary.source, summary.collection, source_hash)

        return DeleteResult(
            success=True,
            source=summary.source,
            collection=summary.collection,
            removed_vectors=removed_vectors,
            removed_chunks=removed_chunks,
            removed_images=removed_images,
            removed_history_rows=removed_history_rows,
            message="deleted",
        )

    def list_collections(self) -> List[Dict[str, Any]]:
        collections: Dict[str, Dict[str, Any]] = {}
        for summary in self.list_documents():
            bucket = collections.setdefault(
                summary.collection,
                {
                    "name": summary.collection,
                    "document_count": 0,
                    "chunk_count": 0,
                    "image_count": 0,
                    "doc_types": {},
                },
            )
            bucket["document_count"] += 1
            bucket["chunk_count"] += summary.chunk_count
            bucket["image_count"] += summary.image_count
            bucket["doc_types"][summary.doc_type] = bucket["doc_types"].get(summary.doc_type, 0) + 1
        if not collections:
            return [
                {
                    "name": self._default_collection_name(),
                    "document_count": 0,
                    "chunk_count": 0,
                    "image_count": 0,
                    "doc_types": {},
                }
            ]
        return list(collections.values())

    def _default_collection_name(self) -> str:
        return str(self.settings.get("dashboard.collection", "default"))

    def _fetch_records(self, collection: Optional[str] = None) -> List[Dict[str, Any]]:
        if hasattr(self.vector_store, "list_records"):
            raw_records = list(self.vector_store.list_records())  # type: ignore[attr-defined]
            return [self._normalize_record(record, collection) for record in raw_records if self._matches_collection(record, collection)]

        collection_obj = getattr(self.vector_store, "_collection", None)
        if collection_obj is None or not hasattr(collection_obj, "get"):
            return []

        try:
            response = collection_obj.get(include=["metadatas", "documents"])
        except TypeError:
            response = collection_obj.get()

        ids = list(response.get("ids", []))
        metadatas = list(response.get("metadatas", []))
        documents = list(response.get("documents", []))
        records: List[Dict[str, Any]] = []
        for index, vector_id in enumerate(ids):
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            document = documents[index] if index < len(documents) else None
            record = {
                "vector_id": vector_id,
                "metadata": metadata,
                "content": document or "",
            }
            if self._matches_collection(record, collection):
                records.append(record)
        return records

    @staticmethod
    def _matches_collection(record: Dict[str, Any], collection: Optional[str]) -> bool:
        if collection is None:
            return True
        metadata = record.get("metadata", {})
        return str(metadata.get("collection", "default")) == str(collection)

    @staticmethod
    def _normalize_record(record: Dict[str, Any], collection: Optional[str]) -> Dict[str, Any]:
        metadata = dict(record.get("metadata") or {})
        normalized = {
            "vector_id": str(record.get("vector_id") or record.get("id") or ""),
            "metadata": metadata,
            "content": str(record.get("content") or record.get("text") or ""),
        }
        if DocumentManager._matches_collection(normalized, collection):
            return normalized
        return normalized

    def _group_records(self, records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            metadata = record.get("metadata", {})
            doc_key = str(
                metadata.get("source_hash")
                or metadata.get("source")
                or record.get("vector_id")
            )
            grouped.setdefault(doc_key, []).append(record)
        for group in grouped.values():
            group.sort(key=lambda item: int(item.get("metadata", {}).get("chunk_index", 0)))
        return grouped

    def _find_group(
        self,
        records: Iterable[Dict[str, Any]],
        doc_id: str,
        collection: Optional[str],
    ) -> Optional[List[Dict[str, Any]]]:
        grouped = self._group_records(records)
        doc_id = str(doc_id)
        for key, group in grouped.items():
            if key == doc_id:
                return group
            metadata = group[0].get("metadata", {}) if group else {}
            if str(metadata.get("source")) == doc_id:
                return group
            if str(metadata.get("source_hash")) == doc_id:
                return group
            if collection and str(metadata.get("collection", "default")) != str(collection):
                continue
        return None

    def _build_summary(self, group: List[Dict[str, Any]], collection: Optional[str]) -> DocumentSummary:
        first = group[0]
        metadata = dict(first.get("metadata") or {})
        source = str(metadata.get("source") or metadata.get("source_path") or first.get("vector_id"))
        title = str(metadata.get("title") or Path(source).stem or source)
        doc_type = str(metadata.get("doc_type") or metadata.get("source_type") or "unknown")
        image_count = 0
        for record in group:
            image_count += len(self._extract_image_refs(record))
        return DocumentSummary(
            doc_id=str(metadata.get("source_hash") or source or first.get("vector_id")),
            source=source,
            title=title,
            collection=str(metadata.get("collection") or collection or self._default_collection_name()),
            doc_type=doc_type,
            chunk_count=len(group),
            image_count=image_count,
            last_modified=str(metadata.get("modification_time") or metadata.get("last_modified") or "" ) or None,
            metadata=metadata,
        )

    def _record_to_chunk(self, record: Dict[str, Any]) -> DocumentChunkDetail:
        metadata = dict(record.get("metadata") or {})
        return DocumentChunkDetail(
            vector_id=str(record.get("vector_id") or ""),
            chunk_id=str(metadata.get("chunk_id") or record.get("vector_id") or ""),
            chunk_index=int(metadata.get("chunk_index", 0)),
            content=str(record.get("content") or ""),
            metadata=metadata,
            image_refs=self._extract_image_refs(record),
        )

    @staticmethod
    def _extract_image_refs(record: Dict[str, Any]) -> List[str]:
        metadata = dict(record.get("metadata") or {})
        refs: List[str] = []
        raw_refs = metadata.get("image_refs") or metadata.get("images") or []
        if isinstance(raw_refs, list):
            for item in raw_refs:
                if isinstance(item, str):
                    refs.append(item)
                elif isinstance(item, dict):
                    image_id = item.get("id") or item.get("image_id")
                    if image_id:
                        refs.append(str(image_id))
        elif raw_refs:
            refs.append(str(raw_refs))
        return refs

    def _delete_from_vector_store(self, vector_ids: List[str], summary: DocumentSummary) -> int:
        if not vector_ids:
            return 0
        collection_obj = getattr(self.vector_store, "_collection", None)
        if collection_obj is not None and hasattr(collection_obj, "delete"):
            try:
                collection_obj.delete(ids=vector_ids)
                return len(vector_ids)
            except Exception:
                pass
        if hasattr(self.vector_store, "delete_by_metadata"):
            try:
                self.vector_store.delete_by_metadata({"source": summary.source})  # type: ignore[attr-defined]
                return len(vector_ids)
            except Exception:
                return 0
        return 0

    def _remove_from_bm25(self, chunk_ids: List[str]) -> int:
        if not chunk_ids:
            return 0
        remover = getattr(self.bm25_indexer, "remove_document", None)
        if callable(remover):
            try:
                return int(remover(chunk_ids=chunk_ids))
            except TypeError:
                try:
                    return int(remover(chunk_ids))
                except Exception:
                    return 0
            except Exception:
                return 0
        return 0

    def _remove_images(self, source_hash: Optional[str], collection: str) -> int:
        remover = getattr(self.image_storage, "remove_images", None)
        if not callable(remover):
            return 0
        try:
            return int(remover(collection=collection, doc_hash=source_hash))
        except TypeError:
            try:
                return int(remover(doc_hash=source_hash))
            except Exception:
                return 0
        except Exception:
            return 0

    def _remove_history_rows(self, source: str, collection: str, source_hash: Optional[str]) -> int:
        if not self.history_db_path.exists():
            return 0
        removed = 0
        try:
            with sqlite3.connect(str(self.history_db_path)) as conn:
                if source_hash:
                    cursor = conn.execute(
                        "DELETE FROM ingestion_history WHERE (source = ? OR source_hash = ?) AND collection = ?",
                        (source, source_hash, collection),
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM ingestion_history WHERE source = ? AND collection = ?",
                        (source, collection),
                    )
                removed = int(cursor.rowcount or 0)
        except sqlite3.Error:
            removed = 0
        return removed
