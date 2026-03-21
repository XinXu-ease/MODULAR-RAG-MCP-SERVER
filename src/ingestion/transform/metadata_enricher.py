from __future__ import annotations

import json
import re
from typing import List, Optional

from src.core.settings import Settings, get_settings
from src.core.trace import TraceContext
from src.core.types import Chunk
from src.libs.llm_client.base import BaseLLM
from src.libs.llm_client.llm_factory import create_llm

from .base_transform import BaseTransform

_STOPWORDS = {
    "the", "and", "that", "with", "from", "this", "have", "are", "for", "you", "your",
    "into", "about", "was", "were", "has", "had", "will", "not", "but", "can", "all",
}


class MetadataEnricher(BaseTransform):
    def __init__(self, settings: Optional[Settings] = None, llm: Optional[BaseLLM] = None):
        self.settings = settings or get_settings()
        self.use_llm = bool(self.settings.get("ingestion.metadata_enricher.use_llm", False))
        self.llm = llm
        if self.use_llm and self.llm is None:
            try:
                self.llm = create_llm(self.settings)
            except Exception:
                self.llm = None

    def transform(self, chunks: List[Chunk], trace: Optional[TraceContext] = None) -> List[Chunk]:
        out: List[Chunk] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            enriched = self._rule_enrich(chunk.content)
            metadata.update(enriched)
            metadata["enriched_by"] = "rule"

            if self.use_llm and self.llm is not None:
                llm_enriched = self._llm_enrich(chunk.content)
                if llm_enriched is not None:
                    metadata.update(llm_enriched)
                    metadata["enriched_by"] = "llm"
                else:
                    metadata["enrich_fallback"] = "llm_failed"

            out.append(
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
            trace.record_stage("metadata_enricher", chunk_count=len(chunks))
        return out

    def _rule_enrich(self, text: str) -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0][:80] if lines else "Untitled Chunk"
        compact = re.sub(r"\s+", " ", text).strip()
        summary = compact[:180] if compact else "Empty chunk"

        words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)]
        unique = []
        seen = set()
        for word in words:
            if word in _STOPWORDS or word in seen:
                continue
            seen.add(word)
            unique.append(word)
            if len(unique) >= 5:
                break
        if not unique:
            unique = ["general"]

        return {"title": title, "summary": summary, "tags": unique}

    def _llm_enrich(self, text: str) -> Optional[dict]:
        try:
            prompt = (
                "Return JSON with keys title, summary, tags (array of strings). "
                "Keep it concise and faithful. Text:\n\n"
                f"{text}"
            )
            response = self.llm.generate(prompt)
            data = json.loads(response)
            if not isinstance(data, dict):
                return None
            title = str(data.get("title", "")).strip()
            summary = str(data.get("summary", "")).strip()
            tags = data.get("tags", [])
            if not isinstance(tags, list):
                return None
            tags = [str(t).strip() for t in tags if str(t).strip()]
            if not title or not summary or not tags:
                return None
            return {"title": title, "summary": summary, "tags": tags}
        except Exception:
            return None
