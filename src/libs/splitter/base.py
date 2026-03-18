from abc import ABC, abstractmethod
from typing import List


class BaseSplitter(ABC):
    """抽象文本切分接口。"""

    @abstractmethod
    def split(self, text: str) -> List[str]:
        """将长文本切分成多个 chunk。"""
        raise NotImplementedError
