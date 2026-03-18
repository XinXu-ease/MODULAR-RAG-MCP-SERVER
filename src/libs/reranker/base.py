from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseReranker(ABC):
    """抽象重排序接口。"""

    @abstractmethod
    def rerank(self, query: str, candidates: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """给定查询和候选文档列表返回重排后的候选。"""
        raise NotImplementedError
