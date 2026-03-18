from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLM(ABC):
    """抽象 LLM 提供者接口。"""

    def __init__(self, model: str, api_key: str = None, api_base: str = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """以聊天格式向模型发送消息并返回文本答复。"""
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """给定文本提示生成响应。"""
        raise NotImplementedError
