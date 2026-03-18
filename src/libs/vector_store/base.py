from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Dict


class BaseVectorStore(ABC):
    """向量库存储的抽象接口。"""

    @abstractmethod
    def add(self, embeddings: Iterable[List[float]], metadatas: Iterable[Dict[str, Any]], ids: Optional[Iterable[str]] = None):
        """批量写入向量及其元数据。"""
        raise NotImplementedError

    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """根据查询向量执行最近邻检索，返回带分数的记录。"""
        raise NotImplementedError
