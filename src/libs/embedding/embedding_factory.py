from typing import Optional

from src.core.settings import Settings, get_settings

from .base import BaseEmbedding
from .openai_embedding import OpenAIEmbedding

_PROVIDER_MAP = {
    "openai": OpenAIEmbedding,
    # 更多 provider 可在此注册
}


def create_embedding(settings: Optional[Settings] = None) -> BaseEmbedding:
    if settings is None:
        settings = get_settings()

    emb_cfg = settings.embedding
    provider = (emb_cfg.provider or "").lower()
    cls = _PROVIDER_MAP.get(provider)
    if cls is None:
        raise ValueError(f"Unsupported embedding provider: {provider}")

    return cls(model=emb_cfg.model, api_key=emb_cfg.api_key, api_base=emb_cfg.api_base)
