from typing import List, Dict, Any

from .base import BaseReranker


class DummyReranker(BaseReranker):
    """简单的示例重排序器，不改变候选顺序。"""
    def rerank(self, query: str, candidates: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        return candidates
