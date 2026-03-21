from src.core.types import Chunk
from src.ingestion.transform.image_captioner import ImageCaptioner


class DummyVision:
    def describe_image(self, image_ref: str, prompt: str):
        return f"caption for {image_ref}"


def test_image_captioner_fallback_disabled():
    captioner = ImageCaptioner()
    chunk = Chunk(id="c", content="x", source="s", chunk_index=0, metadata={"source": "s"}, image_refs=["a.png"])
    out = captioner.transform([chunk])[0]
    assert out.metadata["has_unprocessed_images"] is True


def test_image_captioner_enabled(monkeypatch):
    monkeypatch.setenv("SETTING_INGESTION_IMAGE_CAPTIONER_ENABLED", "true")
    captioner = ImageCaptioner(vision_llm=DummyVision())
    chunk = Chunk(id="c", content="x", source="s", chunk_index=0, metadata={"source": "s"}, image_refs=["a.png"])
    out = captioner.transform([chunk])[0]
    assert out.metadata["has_unprocessed_images"] is False
    assert out.metadata["image_captions"]["a.png"] == "caption for a.png"
