from __future__ import annotations

import time
from typing import Dict, List, Optional

from src.core.types import Chunk

from .dense_encoder import DenseEncoder
from .sparse_encoder import SparseEncoder


class BatchProcessor:
    def __init__(
        self,
        dense_encoder: DenseEncoder,
        sparse_encoder: SparseEncoder,
        batch_size: int = 16,
    ):
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        self.dense_encoder = dense_encoder
        self.sparse_encoder = sparse_encoder
        self.batch_size = batch_size

    def process(self, chunks: List[Chunk]) -> Dict[str, object]:
        dense_vectors: Dict[str, List[float]] = {}
        sparse_vectors: Dict[str, Dict[str, float]] = {}
        batch_metrics: List[Dict[str, object]] = []

        for batch_idx, start in enumerate(range(0, len(chunks), self.batch_size)):
            batch = chunks[start : start + self.batch_size]
            tick = time.perf_counter()

            dense_vectors.update(self.dense_encoder.encode(batch))
            sparse_vectors.update(self.sparse_encoder.encode(batch))

            elapsed_ms = (time.perf_counter() - tick) * 1000
            batch_metrics.append(
                {
                    "batch_index": batch_idx,
                    "chunk_ids": [chunk.id for chunk in batch],
                    "latency_ms": elapsed_ms,
                }
            )

        return {
            "dense_vectors": dense_vectors,
            "sparse_vectors": sparse_vectors,
            "batches": batch_metrics,
        }
