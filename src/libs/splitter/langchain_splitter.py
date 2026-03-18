from typing import List

# newer langchain versions ship the splitter in a separate package
# first try the standalone module installed by requirements
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # fallback to langchain submodule (older layout)
    try:
        from langchain.text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

from .base import BaseSplitter


class LangChainSplitter(BaseSplitter):
    def __init__(self, **kwargs):
        # 默认设置可在 kwargs 中覆盖
        self._splitter = RecursiveCharacterTextSplitter(**kwargs)

    def split(self, text: str) -> List[str]:
        return self._splitter.split_text(text)
