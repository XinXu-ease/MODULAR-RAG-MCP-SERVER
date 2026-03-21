from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.settings import Settings, get_settings
from src.core.trace import TraceContext
from src.core.types import Chunk

from .base_transform import BaseTransform


class ImageCaptioner(BaseTransform):
    def __init__(
        self,
        settings: Optional[Settings] = None,
        vision_llm: Optional[Any] = None,
        prompt_path: Optional[str] = None,
    ):
        self.settings = settings or get_settings()
        self.enabled = bool(self.settings.get("ingestion.image_captioner.enabled", False))
        self.vision_llm = vision_llm
        self.prompt = self._load_prompt(prompt_path)

    def transform(self, chunks: List[Chunk], trace: Optional[TraceContext] = None) -> List[Chunk]:
        result: List[Chunk] = []

        for chunk in chunks:
            metadata: Dict[str, Any] = dict(chunk.metadata)
            refs = list(chunk.image_refs)
            if not refs:
                result.append(chunk)
                continue

            if not self.enabled or self.vision_llm is None:
                metadata["has_unprocessed_images"] = True
                result.append(self._copy_chunk(chunk, metadata))
                continue

            captions: Dict[str, str] = {}
            failed = False
            for ref in refs:
                try:
                    captions[ref] = self._caption_image(ref)
                except Exception:
                    failed = True
                    break

            if failed:
                metadata["has_unprocessed_images"] = True
            else:
                metadata["image_captions"] = captions
                metadata["has_unprocessed_images"] = False

            result.append(self._copy_chunk(chunk, metadata))

        if trace:
            trace.record_stage("image_captioner", chunk_count=len(chunks))

        return result

    def _caption_image(self, image_ref: str) -> str:
        if hasattr(self.vision_llm, "describe_image"):
            return str(self.vision_llm.describe_image(image_ref=image_ref, prompt=self.prompt)).strip()
        if hasattr(self.vision_llm, "generate"):
            return str(self.vision_llm.generate(self.prompt.format(image_ref=image_ref))).strip()
        raise TypeError("vision_llm does not support describe_image/generate")

    @staticmethod
    def _copy_chunk(chunk: Chunk, metadata: Dict[str, Any]) -> Chunk:
        return Chunk(
            id=chunk.id,
            content=chunk.content,
            source=chunk.source,
            chunk_index=chunk.chunk_index,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            metadata=metadata,
            image_refs=list(chunk.image_refs),
        )

    @staticmethod
    def _load_prompt(prompt_path: Optional[str] = None) -> str:
        path = Path(prompt_path) if prompt_path else Path("config/prompts/image_captioning.txt")
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if "{image_ref}" in content:
                return content
            return f"{content}\n\nImage: {{image_ref}}"
        return "Describe this image for retrieval context in one sentence: {image_ref}"
