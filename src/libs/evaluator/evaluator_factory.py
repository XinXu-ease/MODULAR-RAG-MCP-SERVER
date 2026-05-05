from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseEvaluator
from .dummy_evaluator import DummyEvaluator

_PROVIDER_MAP = {
    "dummy": DummyEvaluator,
}


def _load_ragas_evaluator():
    """延迟加载 Ragas 评估器以处理可选依赖。"""
    try:
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        _PROVIDER_MAP["ragas"] = RagasEvaluator
    except ImportError:
        pass


def create_evaluator(settings: Optional[Settings] = None) -> BaseEvaluator:
    """创建评估器实例。
    
    Args:
        settings: 设置对象。如果为 None，使用全局设置。
    
    Returns:
        根据配置选择的评估器实例。
    
    Raises:
        ValueError: 如果指定的评估器后端未找到或不可用。
    """
    if settings is None:
        settings = get_settings()
    
    # 首次调用时延迟加载 ragas（如果可用）
    if "ragas" not in _PROVIDER_MAP:
        _load_ragas_evaluator()
    
    # 从配置中获取评估器后端，默认为 dummy
    provider = getattr(settings, "evaluation_backend", "dummy")
    
    if provider not in _PROVIDER_MAP:
        raise ValueError(
            f"评估器后端 '{provider}' 不可用。可用选项: {list(_PROVIDER_MAP.keys())}"
        )
    
    evaluator_class = _PROVIDER_MAP[provider]
    return evaluator_class()
