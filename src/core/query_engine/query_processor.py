from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ProcessedQuery:
    original_query: str
    normalized_query: str
    keywords: List[str]
    filters: Dict[str, object]


class QueryProcessor:
    token_pattern = re.compile(r"\b\w+\b", flags=re.UNICODE)
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it", "of", "on",
        "or", "that", "the", "this", "to", "was", "what", "when", "where", "which", "who", "why", "will", "with",
        "了", "和", "是", "在", "的", "与", "及", "或", "吗", "呢", "啊", "吧", "把", "被", "对", "有", "没有",
    }

    def process(self, query: str, filters: Optional[Dict[str, object]] = None) -> ProcessedQuery:
        normalized = (query or "").strip()
        tokens = [token.lower() for token in self.token_pattern.findall(normalized)]
        keywords = [token for token in tokens if token not in self.stop_words and len(token) > 1]
        if not keywords:
            keywords = [token for token in tokens if token]

        normalized_filters: Dict[str, object] = {}
        if isinstance(filters, dict):
            normalized_filters = {k: v for k, v in filters.items() if v is not None}

        return ProcessedQuery(
            original_query=query,
            normalized_query=normalized,
            keywords=keywords,
            filters=normalized_filters,
        )
