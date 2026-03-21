from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.trace import TraceContext
from src.core.types import Chunk


class BaseTransform(ABC):
    @abstractmethod
    def transform(self, chunks: List[Chunk], trace: Optional[TraceContext] = None) -> List[Chunk]:
        raise NotImplementedError
