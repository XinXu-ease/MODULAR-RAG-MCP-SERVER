from src.core.types import Chunk
from src.ingestion.embedding.sparse_encoder import SparseEncoder


def test_sparse_encoder_outputs_weights():
    chunks = [Chunk(id="c1", content="coffee coffee brew", source="s", chunk_index=0, metadata={"source": "s"})]
    encoder = SparseEncoder()
    out = encoder.encode(chunks)
    assert "coffee" in out["c1"]
    assert out["c1"]["coffee"] > out["c1"]["brew"]


def test_sparse_encoder_empty_text():
    chunks = [Chunk(id="c1", content="", source="s", chunk_index=0, metadata={"source": "s"})]
    encoder = SparseEncoder()
    out = encoder.encode(chunks)
    assert out["c1"] == {}
