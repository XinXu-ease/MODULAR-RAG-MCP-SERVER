from abc import ABC, abstractmethod
from typing import List, Any


class BaseEmbedding(ABC):
    """抽象 Embedding 提供者接口。"""

    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """将一组文本转为向量列表。"""
        raise NotImplementedError
