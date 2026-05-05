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


def _resolve_settings(settings: Optional[Settings] = None) -> Settings:
    if settings is not None:
        return settings

    try:
        return get_settings()
    except Exception:
        class _FallbackSettings:
            def get(self, key: str, default=None):
                return default

        return _FallbackSettings()  # type: ignore[return-value]


class IngestionPipeline:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = _resolve_settings(settings)
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

    def run(self, source: str, source_type: Optional[str] = None, collection: str = "default", force: bool = False, on_progress: Optional[callable] = None) -> IngestionResult:
        trace = TraceContext(trace_type="ingestion")
        metrics = IngestionMetrics()
        
        import time

        try:
            # Load stage
            load_start = time.perf_counter()
            inferred_type = source_type or self._infer_source_type(source)
            loader = create_loader(inferred_type)
            document = loader.load(source)
            load_ms = (time.perf_counter() - load_start) * 1000
            trace.record_stage("load", elapsed_ms=load_ms, source=source, source_type=inferred_type, method=inferred_type)

            source_hash = document.metadata.get("source_hash", "")
            if not force and self._is_already_ingested(source, source_hash, collection):
                trace.finish()
                if on_progress:
                    on_progress("load", 1, 1)
                return IngestionResult(
                    success=True,
                    source=source,
                    metrics=IngestionMetrics(skipped_chunks=1, total_latency_ms=trace.total_latency_ms),
                    trace_id=trace.trace_id,
                )

            # Split stage
            split_start = time.perf_counter()
            chunks = self.chunker.split_document(document)
            split_ms = (time.perf_counter() - split_start) * 1000
            trace.record_stage("split", elapsed_ms=split_ms, chunk_count=len(chunks), method="recursive")
            if on_progress:
                on_progress("split", 1, 5)

            # Transform stages (refine, enrich, caption)
            transform_start = time.perf_counter()
            chunks = self.refiner.transform(chunks, trace=trace)
            chunks = self.enricher.transform(chunks, trace=trace)
            chunks = self.captioner.transform(chunks, trace=trace)
            transform_ms = (time.perf_counter() - transform_start) * 1000
            trace.record_stage("transform", elapsed_ms=transform_ms, chunk_count=len(chunks), method="multi_stage")
            if on_progress:
                on_progress("transform", 2, 5)

            # Embed stage
            embed_start = time.perf_counter()
            encoded = self.batch.process(chunks)
            dense_vectors = encoded["dense_vectors"]
            sparse_vectors = encoded["sparse_vectors"]
            embed_ms = (time.perf_counter() - embed_start) * 1000
            trace.record_stage("embed", elapsed_ms=embed_ms, chunk_count=len(chunks), method="batch_embedding")
            if on_progress:
                on_progress("embed", 3, 5)

            # Upsert stage
            upsert_start = time.perf_counter()
            self.bm25.build(sparse_vectors, rebuild=False)
            self.vector_upserter.upsert(chunks, dense_vectors, collection=collection)
            upsert_ms = (time.perf_counter() - upsert_start) * 1000
            trace.record_stage("upsert", elapsed_ms=upsert_ms, chunk_count=len(chunks), method="chroma_bm25")

            metrics.total_chunks = len(chunks)
            metrics.total_images = sum(len(chunk.image_refs) for chunk in chunks)
            if on_progress:
                on_progress("upsert", 4, 5)
                on_progress("complete", 5, 5)

            self._record_ingested(source=source, source_hash=source_hash, collection=collection)
            trace.finish()
            metrics.total_latency_ms = trace.total_latency_ms

            return IngestionResult(success=True, source=source, metrics=metrics, trace_id=trace.trace_id)
        except Exception as exc:
            trace.finish()
            metrics.total_latency_ms = trace.total_latency_ms
            if on_progress:
                on_progress("error", 0, 5)
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
