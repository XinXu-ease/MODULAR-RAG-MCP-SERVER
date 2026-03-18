from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseEvaluator(ABC):
    """抽象评估器接口。"""

    @abstractmethod
    def evaluate(self, query: str, retrieved_chunks: List[Any], generated_answer: str, ground_truth: Any = None) -> Dict[str, Any]:
        """执行评估并返回指标字典。"""
        raise NotImplementedError
