from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from src.core.settings import Settings, get_settings
from src.core.trace import TraceContext
from src.core.types import IngestionMetrics, IngestionResult
from src.ingestion.chunking import DocumentChunker
from src.ingestion.embedding import BatchProcessor, DenseEncoder, SparseEncoder
from src.ingestion.loaders import create_loader
from src.ingestion.storage import BM25Indexer, ImageStorage, VectorUpserter
from src.ingestion.transform import ChunkRefiner, ImageCaptioner, MetadataEnricher


class IngestionPipeline:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.chunker = DocumentChunker(self.settings)
        self.refiner = ChunkRefiner(self.settings)
        self.enricher = MetadataEnricher(self.settings)
        self.captioner = ImageCaptioner(self.settings)
        self.dense = DenseEncoder(self.settings)
        self.sparse = SparseEncoder()
        self.batch = BatchProcessor(self.dense, self.sparse, batch_size=int(self.settings.get("ingestion.batch_size", 16)))
        self.bm25 = BM25Indexer(index_dir=self.settings.get("ingestion.bm25_index_dir", "data/db/bm25"))
        self.vector_upserter = VectorUpserter(self.settings)
        self.image_storage = ImageStorage(
            image_root=self.settings.get("ingestion.image_root", "data/images"),
            db_path=self.settings.get("ingestion.image_index_db", "data/db/image_index.db"),
        )
        self.history_db = Path(self.settings.get("ingestion.history_db", "data/db/ingestion_history.db"))
        self.history_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_history_table()

    def run(self, source: str, source_type: Optional[str] = None, collection: str = "default", force: bool = False) -> IngestionResult:
        trace = TraceContext(trace_type="ingestion")
        metrics = IngestionMetrics()

        try:
            inferred_type = source_type or self._infer_source_type(source)
            loader = create_loader(inferred_type)
            document = loader.load(source)
            trace.record_stage("load", source=source, source_type=inferred_type)

            source_hash = document.metadata.get("source_hash", "")
            if not force and self._is_already_ingested(source, source_hash, collection):
                trace.finish()
                return IngestionResult(
                    success=True,
                    source=source,
                    metrics=IngestionMetrics(skipped_chunks=1, total_latency_ms=trace.total_latency_ms),
                    trace_id=trace.trace_id,
                )

            chunks = self.chunker.split_document(document)
            chunks = self.refiner.transform(chunks, trace=trace)
            chunks = self.enricher.transform(chunks, trace=trace)
            chunks = self.captioner.transform(chunks, trace=trace)

            encoded = self.batch.process(chunks)
            dense_vectors = encoded["dense_vectors"]
            sparse_vectors = encoded["sparse_vectors"]

            self.bm25.build(sparse_vectors, rebuild=False)
            self.vector_upserter.upsert(chunks, dense_vectors)

            metrics.total_chunks = len(chunks)
            metrics.total_images = sum(len(chunk.image_refs) for chunk in chunks)
            trace.record_stage("store", chunk_count=len(chunks))

            self._record_ingested(source=source, source_hash=source_hash, collection=collection)
            trace.finish()
            metrics.total_latency_ms = trace.total_latency_ms

            return IngestionResult(success=True, source=source, metrics=metrics, trace_id=trace.trace_id)
        except Exception as exc:
            trace.finish()
            metrics.total_latency_ms = trace.total_latency_ms
            return IngestionResult(success=False, source=source, metrics=metrics, error=str(exc), trace_id=trace.trace_id)

    @staticmethod
    def _infer_source_type(source: str) -> str:
        lowered = source.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return "web"
        if lowered.endswith(".pdf"):
            return "pdf"
        raise ValueError(f"Cannot infer source type from: {source}")

    def _init_history_table(self) -> None:
        with sqlite3.connect(str(self.history_db)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_history (
                    source TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY(source, collection)
                )
                """
            )

    def _is_already_ingested(self, source: str, source_hash: str, collection: str) -> bool:
        with sqlite3.connect(str(self.history_db)) as conn:
            row = conn.execute(
                """
                SELECT source_hash, status FROM ingestion_history
                WHERE source = ? AND collection = ?
                """,
                (source, collection),
            ).fetchone()
        return bool(row and row[0] == source_hash and row[1] == "success")

    def _record_ingested(self, source: str, source_hash: str, collection: str) -> None:
        with sqlite3.connect(str(self.history_db)) as conn:
            conn.execute(
                """
                INSERT INTO ingestion_history(source, source_hash, collection, status)
                VALUES (?, ?, ?, 'success')
                ON CONFLICT(source, collection) DO UPDATE SET
                    source_hash = excluded.source_hash,
                    status = excluded.status
                """,
                (source, source_hash, collection),
            )
