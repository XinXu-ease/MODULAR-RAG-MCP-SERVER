from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

from src.core.types import Chunk


class SparseEncoder:
    token_pattern = re.compile(r"\b\w+\b", flags=re.UNICODE)

    def encode(self, chunks: List[Chunk]) -> Dict[str, Dict[str, float]]:
        outputs: Dict[str, Dict[str, float]] = {}

        for chunk in chunks:
            tokens = [t.lower() for t in self.token_pattern.findall(chunk.content)]
            if not tokens:
                outputs[chunk.id] = {}
                continue

            counter = Counter(tokens)
            length = len(tokens)
            outputs[chunk.id] = {term: tf / length for term, tf in counter.items()}

        return outputs

    @staticmethod
    def build_query_vector(query: str) -> Dict[str, float]:
        tokens = [tok.lower() for tok in re.findall(r"\b\w+\b", query)]
        if not tokens:
            return {}
        counter = Counter(tokens)
        length = len(tokens)
        return {term: (count / length) * (1.0 + math.log1p(count)) for term, count in counter.items()}
