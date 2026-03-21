from typing import List

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

from .base import BaseEmbedding


class OpenAIEmbedding(BaseEmbedding):
    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        super().__init__(model, api_key, api_base, **kwargs)
        if openai is not None:
            if api_key:
                openai.api_key = api_key
            if api_base:
                openai.api_base = api_base

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        if openai is None:
            raise RuntimeError("openai package is required for OpenAI embeddings. Install: pip install openai")
        resp = openai.Embedding.create(model=self.model, input=texts, **kwargs)
        return [item["embedding"] for item in resp.data]
