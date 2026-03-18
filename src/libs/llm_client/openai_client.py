from typing import List, Dict, Any

import openai

from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """简单的 OpenAI Chat/Completion 封装，兼容常见用法。"""

    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        super().__init__(model, api_key, api_base, **kwargs)
        if api_key:
            openai.api_key = api_key
        if api_base:
            openai.api_base = api_base

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        resp = openai.ChatCompletion.create(model=self.model, messages=messages, **kwargs)
        return resp.choices[0].message.get("content", "")

    def generate(self, prompt: str, **kwargs) -> str:
        # 一般使用 Completion 端点
        resp = openai.Completion.create(model=self.model, prompt=prompt, **kwargs)
        return resp.choices[0].text
