from __future__ import annotations

import hashlib
from typing import List, Optional

from src.core.settings import Settings, get_settings
from src.core.types import Chunk, Document
from src.libs.splitter.base import BaseSplitter
from src.libs.splitter.splitter_factory import create_splitter


class DocumentChunker:
    """Convert loaded Document into typed Chunk records."""

    def __init__(self, settings: Optional[Settings] = None, splitter: Optional[BaseSplitter] = None):
        self.settings = settings or get_settings()
        self.splitter = splitter or create_splitter(self.settings)

    def split_document(self, document: Document) -> List[Chunk]:
        raw_chunks = self.splitter.split(document.text)
        chunks: List[Chunk] = []
        cursor = 0

        for index, text in enumerate(raw_chunks):
            chunk_text = text.strip()
            if not chunk_text:
                continue

            start_offset = document.text.find(chunk_text, cursor)
            if start_offset < 0:
                start_offset = cursor
            end_offset = start_offset + len(chunk_text)
            cursor = end_offset

            chunk = Chunk(
                id=self._generate_chunk_id(document.id, index, chunk_text),
                content=chunk_text,
                source=document.metadata.get("source", document.id),
                chunk_index=index,
                start_offset=start_offset,
                end_offset=end_offset,
                metadata=self._inherit_metadata(document, index),
                image_refs=list(document.metadata.get("images", [])),
            )
            chunks.append(chunk)

        return chunks

    @staticmethod
    def _generate_chunk_id(doc_id: str, index: int, content: str) -> str:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        return f"{doc_id}_{index:04d}_{digest}"

    @staticmethod
    def _inherit_metadata(document: Document, chunk_index: int) -> dict:
        metadata = dict(document.metadata)
        metadata["chunk_index"] = chunk_index
        metadata["source_ref"] = document.id
        return metadata
