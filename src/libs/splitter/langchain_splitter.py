from typing import List

from .base import BaseSplitter


class _SimpleSplitter:
    """Fallback splitter when langchain is unavailable."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100, **kwargs):
        self.chunk_size = max(int(chunk_size), 1)
        self.chunk_overlap = max(min(int(chunk_overlap), self.chunk_size - 1), 0)

    def split_text(self, text: str) -> List[str]:
        text = text or ""
        if len(text) <= self.chunk_size:
            return [text] if text else []

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks


try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
except ImportError:
    try:
        from langchain.text_splitters import RecursiveCharacterTextSplitter  # type: ignore
    except ImportError:
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore
        except ImportError:
            RecursiveCharacterTextSplitter = _SimpleSplitter  # type: ignore


class LangChainSplitter(BaseSplitter):
    def __init__(self, **kwargs):
        self._splitter = RecursiveCharacterTextSplitter(**kwargs)

    def split(self, text: str) -> List[str]:
        return self._splitter.split_text(text)
