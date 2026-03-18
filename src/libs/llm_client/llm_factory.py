from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseLLM
from .openai_client import OpenAILLM


# registry could be extended later
_PROVIDER_MAP = {
    "openai": OpenAILLM,
    # "ollama": OllamaLLM, # placeholder
}


def create_llm(settings: Optional[Settings] = None) -> BaseLLM:
    """根据配置返回对应的 BaseLLM 实例。"""
    if settings is None:
        settings = get_settings()

    llm_cfg = settings.llm
    provider = (llm_cfg.provider or "").lower()
    cls = _PROVIDER_MAP.get(provider)
    if cls is None:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return cls(
        model=llm_cfg.model,
        api_key=llm_cfg.api_key,
        api_base=llm_cfg.api_base,
    )
