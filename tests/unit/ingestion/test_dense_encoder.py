from src.core.types import Chunk
from src.ingestion.embedding.dense_encoder import DenseEncoder


class DummyEmbedding:
    def embed(self, texts, **kwargs):
        return [[float(i), float(i + 1)] for i, _ in enumerate(texts)]


def test_dense_encoder_output_shape():
    chunks = [
        Chunk(id="c1", content="a", source="s", chunk_index=0, metadata={"source": "s"}),
        Chunk(id="c2", content="b", source="s", chunk_index=1, metadata={"source": "s"}),
    ]
    encoder = DenseEncoder(embedding_client=DummyEmbedding())
    out = encoder.encode(chunks)
    assert set(out.keys()) == {"c1", "c2"}
    assert len(out["c1"]) == 2
