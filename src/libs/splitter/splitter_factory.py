from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseSplitter
from .langchain_splitter import LangChainSplitter

_PROVIDER_MAP = {
    "langchain": LangChainSplitter,
}


def create_splitter(settings: Optional[Settings] = None) -> BaseSplitter:
    if settings is None:
        settings = get_settings()

    # 为兼容，使用固定的 provider 名称
    cls = _PROVIDER_MAP.get("langchain")
    return cls()
