from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from src.core.settings import Settings, get_settings
from src.core.trace import TraceContext
from src.core.types import Chunk
from src.libs.llm_client.base import BaseLLM
from src.libs.llm_client.llm_factory import create_llm

from .base_transform import BaseTransform


class ChunkRefiner(BaseTransform):
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm: Optional[BaseLLM] = None,
        prompt_path: Optional[str] = None,
    ):
        self.settings = settings or get_settings()
        self.use_llm = bool(self.settings.get("ingestion.chunk_refiner.use_llm", False))
        self.llm = llm
        if self.use_llm and self.llm is None:
            try:
                self.llm = create_llm(self.settings)
            except Exception:
                self.llm = None
        self.prompt = self._load_prompt(prompt_path)

    def transform(self, chunks: List[Chunk], trace: Optional[TraceContext] = None) -> List[Chunk]:
        refined_chunks: List[Chunk] = []

        for chunk in chunks:
            metadata = dict(chunk.metadata)
            try:
                rule_refined = self._rule_based_refine(chunk.content)
                final_text = rule_refined
                refined_by = "rule"

                if self.use_llm and self.llm is not None:
                    llm_text = self._llm_refine(rule_refined, trace)
                    if llm_text:
                        final_text = llm_text
                        refined_by = "llm"

                metadata["refined_by"] = refined_by
                refined_chunks.append(
                    Chunk(
                        id=chunk.id,
                        content=final_text,
                        source=chunk.source,
                        chunk_index=chunk.chunk_index,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        metadata=metadata,
                        image_refs=list(chunk.image_refs),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive fallback
                metadata["refined_by"] = "rule"
                metadata["fallback_reason"] = str(exc)
                refined_chunks.append(
                    Chunk(
                        id=chunk.id,
                        content=chunk.content,
                        source=chunk.source,
                        chunk_index=chunk.chunk_index,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        metadata=metadata,
                        image_refs=list(chunk.image_refs),
                    )
                )

        if trace:
            trace.record_stage("chunk_refiner", chunk_count=len(chunks))

        return refined_chunks

    def _rule_based_refine(self, text: str) -> str:
        parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
        cleaned_parts: List[str] = []

        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                cleaned_parts.append(part)
                continue

            segment = re.sub(r"<!--.*?-->", " ", part, flags=re.DOTALL)
            segment = re.sub(r"^\s*(page|页码)\s*\d+\s*$", "", segment, flags=re.IGNORECASE | re.MULTILINE)
            segment = re.sub(r"^[\-=]{3,}$", "", segment, flags=re.MULTILINE)
            segment = re.sub(r"[ \t]+", " ", segment)
            segment = re.sub(r"\n{3,}", "\n\n", segment)
            cleaned_parts.append(segment.strip())

        return "\n\n".join(filter(None, cleaned_parts)).strip()

    def _llm_refine(self, text: str, trace: Optional[TraceContext] = None) -> Optional[str]:
        if self.llm is None:
            return None

        try:
            prompt = self.prompt.format(text=text)
            response = self.llm.generate(prompt)
            result = (response or "").strip()
            if trace:
                trace.record_stage("chunk_refiner_llm", success=bool(result))
            return result or None
        except Exception as exc:  # pragma: no cover - api failures
            if trace:
                trace.record_stage("chunk_refiner_llm", success=False, error=str(exc))
            return None

    def _load_prompt(self, prompt_path: Optional[str] = None) -> str:
        if prompt_path:
            path = Path(prompt_path)
        else:
            path = Path("config/prompts/chunk_refinement.txt")

        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if "{text}" in content:
                return content
            return f"{content}\n\n{{text}}"

        return "Please clean and normalize the following chunk without losing facts:\n\n{text}"
