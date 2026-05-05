from src.core.types import Chunk, Document
from src.ingestion.pipeline import IngestionPipeline


class DummyLoader:
    def load(self, source: str):
        return Document(id="d1", text="hello world", metadata={"source": source, "source_hash": "h1", "images": []})


class DummyChunker:
    def split_document(self, document):
        return [Chunk(id="c1", content="hello", source=document.metadata["source"], chunk_index=0, metadata={"source": document.metadata["source"]})]


class Passthrough:
    def transform(self, chunks, trace=None):
        return chunks


class DummyBatch:
    def process(self, chunks):
        return {"dense_vectors": {"c1": [0.1, 0.2]}, "sparse_vectors": {"c1": {"hello": 1.0}}, "batches": []}


class DummyBM25:
    def build(self, sparse_vectors, rebuild=False):
        self.last = sparse_vectors


class DummyUpserter:
    def upsert(self, chunks, dense_vectors, collection="default"):
        return ["id1"]


def test_ingestion_pipeline_mvp(monkeypatch, tmp_path):
    monkeypatch.setattr("src.ingestion.pipeline.create_loader", lambda source_type: DummyLoader())

    pipeline = IngestionPipeline()
    pipeline.chunker = DummyChunker()
    pipeline.refiner = Passthrough()
    pipeline.enricher = Passthrough()
    pipeline.captioner = Passthrough()
    pipeline.batch = DummyBatch()
    pipeline.bm25 = DummyBM25()
    pipeline.vector_upserter = DummyUpserter()
    pipeline.history_db = tmp_path / "history.db"
    pipeline._init_history_table()

    result = pipeline.run(source="x.pdf", collection="test", force=False)
    assert result.success is True
    assert result.metrics.total_chunks == 1

    result2 = pipeline.run(source="x.pdf", collection="test", force=False)
    assert result2.metrics.skipped_chunks == 1


def test_ingestion_pipeline_infers_website_urls():
    assert IngestionPipeline._infer_source_type("https://www.hariousa.com/recipes/v60") == "web"
    assert IngestionPipeline._infer_source_type("http://www.hariousa.com/recipes/v60") == "web"
