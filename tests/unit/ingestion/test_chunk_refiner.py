from src.core.types import Chunk
from src.ingestion.transform.chunk_refiner import ChunkRefiner


class DummyLLM:
    def generate(self, prompt: str, **kwargs) -> str:
        return "LLM refined text"


class FailingLLM:
    def generate(self, prompt: str, **kwargs) -> str:
        raise RuntimeError("boom")


def _chunk(text: str) -> Chunk:
    return Chunk(id="c1", content=text, source="s", chunk_index=0, metadata={"source": "s"})


def test_chunk_refiner_rule_mode_preserves_code_block():
    refiner = ChunkRefiner()
    noisy = """Page 1\n\n<!-- hidden -->\ntext\n\n```python\nprint(1)\n```"""
    out = refiner.transform([_chunk(noisy)])[0]
    assert "hidden" not in out.content
    assert "```python" in out.content
    assert out.metadata["refined_by"] == "rule"


def test_chunk_refiner_llm_mode(monkeypatch):
    monkeypatch.setenv("SETTING_INGESTION_CHUNK_REFINER_USE_LLM", "true")
    refiner = ChunkRefiner(llm=DummyLLM())
    out = refiner.transform([_chunk("hello")])[0]
    assert out.content == "LLM refined text"
    assert out.metadata["refined_by"] == "llm"


def test_chunk_refiner_llm_fallback(monkeypatch):
    monkeypatch.setenv("SETTING_INGESTION_CHUNK_REFINER_USE_LLM", "true")
    refiner = ChunkRefiner(llm=FailingLLM())
    out = refiner.transform([_chunk("hello")])[0]
    assert out.metadata["refined_by"] == "rule"
