from typing import Literal

from .base import BaseLoader


def create_loader(source_type: Literal["pdf", "web", "website"] = "pdf") -> BaseLoader:
    normalized = source_type.lower()
    if normalized == "pdf":
        from .pdf_loader import PDFLoader

        return PDFLoader()
    if normalized in {"web", "website"}:
        from .web_loader import WebLoader

        return WebLoader()
    raise ValueError(f"Unsupported loader source type: {source_type}")
