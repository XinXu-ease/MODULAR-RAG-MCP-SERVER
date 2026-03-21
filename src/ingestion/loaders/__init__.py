from .base import BaseLoader
from .factory import create_loader

__all__ = ["BaseLoader", "PDFLoader", "WebLoader", "create_loader"]


def __getattr__(name: str):
    if name == "PDFLoader":
        from .pdf_loader import PDFLoader

        return PDFLoader
    if name == "WebLoader":
        from .web_loader import WebLoader

        return WebLoader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
