from typing import List

import openai

from .base import BaseEmbedding


class OpenAIEmbedding(BaseEmbedding):
    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        super().__init__(model, api_key, api_base, **kwargs)
        if api_key:
            openai.api_key = api_key
        if api_base:
            openai.api_base = api_base

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        # OpenAI最近的向量端点支持批量输入
        resp = openai.Embedding.create(model=self.model, input=texts, **kwargs)
        return [item["embedding"] for item in resp.data]
