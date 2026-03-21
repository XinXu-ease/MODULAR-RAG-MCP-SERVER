from src.core.types import Chunk
from src.ingestion.embedding.batch_processor import BatchProcessor


class DummyDense:
    def encode(self, chunks):
        return {chunk.id: [1.0, 2.0] for chunk in chunks}


class DummySparse:
    def encode(self, chunks):
        return {chunk.id: {"x": 1.0} for chunk in chunks}


def test_batch_processor_batch_split_order():
    chunks = [Chunk(id=f"c{i}", content="x", source="s", chunk_index=i, metadata={"source": "s"}) for i in range(5)]
    proc = BatchProcessor(dense_encoder=DummyDense(), sparse_encoder=DummySparse(), batch_size=2)
    out = proc.process(chunks)
    assert len(out["batches"]) == 3
    assert out["batches"][0]["chunk_ids"] == ["c0", "c1"]
    assert out["batches"][2]["chunk_ids"] == ["c4"]
