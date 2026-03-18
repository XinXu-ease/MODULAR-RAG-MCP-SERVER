from typing import Any, Dict, List

from .base import BaseEvaluator


class DummyEvaluator(BaseEvaluator):
    """返回固定空指标的占位评估器。"""

    def evaluate(self, query: str, retrieved_chunks: List[Any], generated_answer: str, ground_truth: Any = None) -> Dict[str, Any]:
        return {"dummy": True}
