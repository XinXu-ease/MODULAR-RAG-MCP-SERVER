from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class ImageStorage:
    def __init__(self, image_root: str = "data/images", db_path: str = "data/db/image_index.db"):
        self.image_root = Path(image_root)
        self.image_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS image_index (
                    image_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    collection TEXT,
                    doc_hash TEXT,
                    page_num INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collection ON image_index(collection);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON image_index(doc_hash);")

    def save_image(
        self,
        image_bytes: bytes,
        collection: str = "default",
        image_id: Optional[str] = None,
        doc_hash: Optional[str] = None,
        page_num: Optional[int] = None,
        extension: str = ".bin",
    ) -> str:
        image_id = image_id or hashlib.sha256(image_bytes).hexdigest()
        collection_dir = self.image_root / collection
        collection_dir.mkdir(parents=True, exist_ok=True)

        normalized_ext = extension if extension.startswith(".") else f".{extension}"
        file_path = collection_dir / f"{image_id}{normalized_ext}"
        file_path.write_bytes(image_bytes)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO image_index(image_id, file_path, collection, doc_hash, page_num)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(image_id) DO UPDATE SET
                    file_path = excluded.file_path,
                    collection = excluded.collection,
                    doc_hash = excluded.doc_hash,
                    page_num = excluded.page_num
                """,
                (image_id, str(file_path), collection, doc_hash, page_num),
            )

        return image_id

    def get_path(self, image_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT file_path FROM image_index WHERE image_id = ?", (image_id,)).fetchone()
            return row[0] if row else None

    def list_images(self, collection: Optional[str] = None, doc_hash: Optional[str] = None) -> List[Dict[str, object]]:
        where = []
        params = []
        if collection:
            where.append("collection = ?")
            params.append(collection)
        if doc_hash:
            where.append("doc_hash = ?")
            params.append(doc_hash)

        sql = "SELECT image_id, file_path, collection, doc_hash, page_num FROM image_index"
        if where:
            sql += " WHERE " + " AND ".join(where)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "image_id": row[0],
                "file_path": row[1],
                "collection": row[2],
                "doc_hash": row[3],
                "page_num": row[4],
            }
            for row in rows
        ]
