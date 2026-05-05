from __future__ import annotations

import sqlite3

from src.ingestion.document_manager import DocumentManager


class FakeCollection:
    def __init__(self, records):
        self._records = records
        self.deleted_ids = []

    def get(self, include=None):
        return {
            "ids": [record["id"] for record in self._records],
            "metadatas": [record["metadata"] for record in self._records],
            "documents": [record["document"] for record in self._records],
        }

    def delete(self, ids=None, where=None):
        if ids:
            self.deleted_ids.extend(ids)


class FakeVectorStore:
    def __init__(self, records):
        self._collection = FakeCollection(records)


class FakeBM25Indexer:
    def __init__(self):
        self.removed = []

    def remove_document(self, chunk_ids=None):
        self.removed.append(list(chunk_ids or []))
        return len(chunk_ids or [])


class FakeImageStorage:
    def __init__(self):
        self.calls = []

    def list_images(self, collection=None, doc_hash=None):
        return []

    def remove_images(self, collection=None, doc_hash=None):
        self.calls.append((collection, doc_hash))
        return 1 if doc_hash else 0


def _records():
    return [
        {
            "id": "vector-1",
            "metadata": {
                "source": "docs/manual.pdf",
                "source_hash": "hash-a",
                "title": "Manual",
                "doc_type": "pdf",
                "collection": "default",
                "chunk_index": 0,
                "chunk_id": "chunk-a-0",
                "image_refs": ["img-1"],
            },
            "document": "Chunk one",
        },
        {
            "id": "vector-2",
            "metadata": {
                "source": "docs/manual.pdf",
                "source_hash": "hash-a",
                "title": "Manual",
                "doc_type": "pdf",
                "collection": "default",
                "chunk_index": 1,
                "chunk_id": "chunk-a-1",
                "image_refs": [],
            },
            "document": "Chunk two",
        },
        {
            "id": "vector-3",
            "metadata": {
                "source": "https://example.com/guide",
                "source_hash": "hash-b",
                "title": "Guide",
                "doc_type": "website",
                "collection": "default",
                "chunk_index": 0,
                "chunk_id": "chunk-b-0",
            },
            "document": "Web chunk",
        },
    ]


def test_document_manager_groups_documents_and_details(tmp_path):
    history_db = tmp_path / "ingestion_history.db"
    with sqlite3.connect(str(history_db)) as conn:
        conn.execute(
            "CREATE TABLE ingestion_history(source TEXT, source_hash TEXT, collection TEXT, status TEXT)"
        )
    manager = DocumentManager(
        vector_store=FakeVectorStore(_records()),
        bm25_indexer=FakeBM25Indexer(),
        image_storage=FakeImageStorage(),
        history_db_path=str(history_db),
    )

    docs = manager.list_documents()
    assert len(docs) == 2
    assert docs[0].chunk_count in {1, 2}

    detail = manager.get_document_detail("hash-a")
    assert detail.doc_id == "hash-a"
    assert len(detail.chunks) == 2
    assert detail.chunks[0].chunk_index == 0
    assert detail.image_count == 1

    stats = manager.get_collection_stats()
    assert stats.document_count == 2
    assert stats.chunk_count == 3
    assert stats.doc_types["pdf"] == 1
    assert stats.doc_types["website"] == 1


def test_document_manager_delete_document_uses_all_backends(tmp_path):
    history_db = tmp_path / "ingestion_history.db"
    with sqlite3.connect(str(history_db)) as conn:
        conn.execute(
            "CREATE TABLE ingestion_history(source TEXT, source_hash TEXT, collection TEXT, status TEXT)"
        )
    manager = DocumentManager(
        vector_store=FakeVectorStore(_records()),
        bm25_indexer=FakeBM25Indexer(),
        image_storage=FakeImageStorage(),
        history_db_path=str(history_db),
    )

    with sqlite3.connect(str(history_db)) as conn:
        conn.execute("INSERT INTO ingestion_history VALUES (?, ?, ?, ?)", ("docs/manual.pdf", "hash-a", "default", "success"))
        conn.commit()

    result = manager.delete_document("docs/manual.pdf")
    assert result.success is True
    assert result.removed_vectors == 2
    assert result.removed_chunks == 2
    assert result.removed_images == 1
    assert result.removed_history_rows >= 1
    assert result.message == "deleted"
