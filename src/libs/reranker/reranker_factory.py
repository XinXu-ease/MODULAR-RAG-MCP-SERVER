from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseReranker
from .dummy_reranker import DummyReranker

_PROVIDER_MAP = {
    "dummy": DummyReranker,
}


def create_reranker(settings: Optional[Settings] = None) -> BaseReranker:
    if settings is None:
        settings = get_settings()

    # 暂时只支持 dummy
    return DummyReranker()
