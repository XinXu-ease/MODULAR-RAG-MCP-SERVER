from typing import Any, Dict, List

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """Simple OpenAI chat/completion wrapper."""

    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        super().__init__(model, api_key, api_base, **kwargs)
        if openai is not None:
            if api_key:
                openai.api_key = api_key
            if api_base:
                openai.api_base = api_base

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        if openai is None:
            raise RuntimeError("openai package is required for OpenAI chat. Install: pip install openai")
        resp = openai.ChatCompletion.create(model=self.model, messages=messages, **kwargs)
        return resp.choices[0].message.get("content", "")

    def generate(self, prompt: str, **kwargs) -> str:
        if openai is None:
            raise RuntimeError("openai package is required for OpenAI generate. Install: pip install openai")
        resp = openai.Completion.create(model=self.model, prompt=prompt, **kwargs)
        return resp.choices[0].text
