from src.core.types import Chunk
from src.ingestion.transform.metadata_enricher import MetadataEnricher


class DummyLLM:
    def generate(self, prompt: str, **kwargs) -> str:
        return '{"title":"T","summary":"S","tags":["a","b"]}'


def test_metadata_enricher_rule_contract():
    enricher = MetadataEnricher()
    chunk = Chunk(id="c", content="Coffee brewing guide for V60", source="s", chunk_index=0, metadata={"source": "s"})
    out = enricher.transform([chunk])[0]
    assert out.metadata["title"]
    assert out.metadata["summary"]
    assert out.metadata["tags"]


def test_metadata_enricher_llm_contract(monkeypatch):
    monkeypatch.setenv("SETTING_INGESTION_METADATA_ENRICHER_USE_LLM", "true")
    enricher = MetadataEnricher(llm=DummyLLM())
    chunk = Chunk(id="c", content="Coffee brewing guide for V60", source="s", chunk_index=0, metadata={"source": "s"})
    out = enricher.transform([chunk])[0]
    assert out.metadata["enriched_by"] == "llm"
    assert out.metadata["title"] == "T"
