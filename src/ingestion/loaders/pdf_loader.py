import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.core.types import Document

from .base import BaseLoader

try:
    from markitdown import MarkItDown
except ImportError:  # pragma: no cover - dependency availability varies
    MarkItDown = None


def _default_pdf_parser(source: str) -> str:
    if MarkItDown is None:
        raise RuntimeError(
            "markitdown is required for PDF loading. Install it with `pip install markitdown`."
        )

    result = MarkItDown().convert(source)
    text = getattr(result, "text_content", None) or getattr(result, "text", None)
    if not text:
        raise RuntimeError(f"No text content extracted from PDF: {source}")
    return text


class PDFLoader(BaseLoader):
    """Load local PDF files into normalized documents."""

    def __init__(self, parser: Optional[Callable[[str], str]] = None):
        self._parser = parser or _default_pdf_parser

    def load(self, source: str) -> Document:
        if not self.validate(source):
            raise ValueError(f"Invalid PDF source: {source}")

        source_path = Path(source)
        markdown_text = self._parser(str(source_path))
        metadata = {
            "doc_type": "pdf",
            "source": str(source_path),
            "source_hash": self._compute_hash(source_path),
            "title": self._extract_title(markdown_text, source_path),
            "file_size": source_path.stat().st_size,
            "modification_time": datetime.fromtimestamp(
                source_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "page_count": self._count_pages(markdown_text),
            "images": self._extract_images(markdown_text),
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }

        return Document(
            id=f"pdf_{hashlib.md5(str(source_path).encode('utf-8')).hexdigest()}",
            text=markdown_text,
            metadata=metadata,
        )

    def validate(self, source: str) -> bool:
        source_path = Path(source)
        return source_path.exists() and source_path.is_file() and source_path.suffix.lower() == ".pdf"

    @staticmethod
    def _compute_hash(source_path: Path) -> str:
        sha256 = hashlib.sha256()
        with source_path.open("rb") as handle:
            for block in iter(lambda: handle.read(8192), b""):
                sha256.update(block)
        return sha256.hexdigest()

    @staticmethod
    def _extract_title(markdown_text: str, source_path: Path) -> str:
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return source_path.stem

    @staticmethod
    def _count_pages(markdown_text: str) -> int:
        page_markers = re.findall(r"<!--\s*[Pp]age\b.*?-->", markdown_text)
        return max(len(page_markers), 1)

    @staticmethod
    def _extract_images(markdown_text: str) -> list[str]:
        pattern = r"!\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif|webp))\)"
        return re.findall(pattern, markdown_text, flags=re.IGNORECASE)
