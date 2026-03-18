from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseEvaluator
from .dummy_evaluator import DummyEvaluator

_PROVIDER_MAP = {
    "dummy": DummyEvaluator,
}


def create_evaluator(settings: Optional[Settings] = None) -> BaseEvaluator:
    if settings is None:
        settings = get_settings()
    # 目前仅支持 dummy
    return DummyEvaluator()
