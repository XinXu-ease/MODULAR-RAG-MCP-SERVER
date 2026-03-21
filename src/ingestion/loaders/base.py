from abc import ABC, abstractmethod

from src.core.types import Document


class BaseLoader(ABC):
    """Abstract ingestion loader interface."""

    @abstractmethod
    def load(self, source: str) -> Document:
        """Load a source into a normalized document."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, source: str) -> bool:
        """Validate whether a source can be loaded."""
        raise NotImplementedError
