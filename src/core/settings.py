"""
Configuration Management System

负责加载、验证、管理整个系统的配置。
遵循分层可插拔的设计理念：允许通过配置文件动态指定各组件的后端实现。
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict

try:
    import yaml
except ImportError:
    yaml = None

from .types import (
    LLMConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    RetrievalConfig,
)


class Settings:
    """
    全局配置管理器。
    
    采用"先读 YAML，再读环境变量，再用 defaults"的层级加载策略，
    确保配置的灵活性与简洁性。
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器。
        
        Args:
            config_file: 配置文件路径。若为 None，在以下位置搜索：
                        - ./config/settings.yaml
                        - ~/.smart_knowledge_hub/settings.yaml
                        - /etc/smart_knowledge_hub/settings.yaml
        """
        if config_file is None:
            config_file = self._find_config_file()
        
        # 默认配置（最基础的可运行配置）
        self._defaults = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "api_base": "https://opeai.api",
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_base": "https://litellm.oit.duke.edu/v1",
            },
            "vector_store": {
                "backend": "chroma",
                "persist_directory": "data/db/chroma",
            },
            "retrieval": {
                "top_k": 10,
                "sparse_backend": "bm25",
                "fusion_algorithm": "rrf",
                "rerank_backend": None,
            },
            "observability": {
                "enabled": True,
                "logging": {
                    "log_file": "logs/traces.jsonl",
                    "log_level": "INFO",
                },
                "detail_level": "standard",
            },
            "dashboard": {
                "enabled": True,
                "port": 8501,
                "traces_dir": "logs",
                "auto_refresh": True,
                "refresh_interval": 5,
            },
        }
        
        # 加载用户配置
        self._user_config = {}
        if config_file and os.path.exists(config_file):
            self._user_config = self._load_config_file(config_file)
        
        # 层级合并
        self._config = self._deep_merge(self._defaults, self._user_config)
        
        # 从环境变量覆盖（支持 SETTING_SECTION_KEY=value 格式）
        self._override_from_env()
    
    @staticmethod
    def _find_config_file() -> Optional[str]:
        """搜索配置文件"""
        candidates = [
            "config/settings.yaml",
            os.path.expanduser("~/.smart_knowledge_hub/settings.yaml"),
            "/etc/smart_knowledge_hub/settings.yaml",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None  # 没找到，将使用 defaults
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """加载配置文件 (YAML 或 JSON)"""
        path = Path(file_path)
        
        if path.suffix.lower() in [".yaml", ".yml"]:
            if yaml is None:
                raise ImportError(
                    "PyYAML is required to load .yaml config files. "
                    "Install it with: pip install pyyaml"
                )
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Settings._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _override_from_env(self):
        """从环境变量覆盖配置 (支持 SETTING_SECTION_KEY=value 格式)"""
        for key, value in os.environ.items():
            if key.startswith("SETTING_"):
                parts = key[8:].lower().split("_")  # 去掉 'SETTING_' 前缀
                if len(parts) >= 2:
                    section = parts[0]
                    config_key = "_".join(parts[1:])
                    
                    if section in self._config and isinstance(self._config[section], dict):
                        self._config[section][config_key] = value
    
    # ========================================================================
    # 配置访问接口
    # ========================================================================
    
    @property
    def llm(self) -> LLMConfig:
        """获取 LLM 配置"""
        cfg = self._config.get("llm", {})
        return LLMConfig(
            provider=cfg.get("provider", "ollama"),
            model=cfg.get("model", "llama2"),
            api_key=cfg.get("api_key"),
            api_base=cfg.get("api_base"),
            deployment_name=cfg.get("deployment_name"),
        )
    
    @property
    def embedding(self) -> EmbeddingConfig:
        """获取 Embedding 配置"""
        cfg = self._config.get("embedding", {})
        return EmbeddingConfig(
            provider=cfg.get("provider", "ollama"),
            model=cfg.get("model", "nomic-embed-text"),
            api_key=cfg.get("api_key"),
            api_base=cfg.get("api_base"),
            dimension=cfg.get("dimension", 384),  # Ollama 默认输出 384 维
        )
    
    @property
    def vector_store(self) -> VectorStoreConfig:
        """获取向量库配置"""
        cfg = self._config.get("vector_store", {})
        return VectorStoreConfig(
            backend=cfg.get("backend", "chroma"),
            persist_directory=cfg.get("persist_directory", "data/db/chroma"),
        )
    
    @property
    def retrieval(self) -> RetrievalConfig:
        """获取检索配置"""
        cfg = self._config.get("retrieval", {})
        return RetrievalConfig(
            top_k=cfg.get("top_k", 10),
            sparse_backend=cfg.get("sparse_backend", "bm25"),
            fusion_algorithm=cfg.get("fusion_algorithm", "rrf"),
            rerank_backend=cfg.get("rerank_backend"),
        )
    
    @property
    def observability(self) -> Dict[str, Any]:
        """获取可观测性配置"""
        return self._config.get("observability", {})
    
    @property
    def dashboard(self) -> Dict[str, Any]:
        """获取 Dashboard 配置"""
        return self._config.get("dashboard", {})
    
    def get(self, key: str, default: Any = None) -> Any:
        """通用 get 方法（支持点号路径，如 'llm.provider'）"""
        keys = key.split(".")
        value = self._config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        return self._config.copy()
    
    def __repr__(self) -> str:
        """调试输出（不显示敏感信息）"""
        display_config = {
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
            },
            "embedding": {
                "provider": self.embedding.provider,
                "model": self.embedding.model,
            },
            "vector_store": {
                "backend": self.vector_store.backend,
            },
            "retrieval": {
                "top_k": self.retrieval.top_k,
                "fusion_algorithm": self.retrieval.fusion_algorithm,
            },
        }
        return f"Settings({json.dumps(display_config, indent=2)})"


# 全局单例
_global_settings: Optional[Settings] = None


def get_settings(config_file: Optional[str] = None) -> Settings:
    """
    获取全局 Settings 单例。
    
    第一次调用时初始化，之后返回同一实例。
    若需要重新加载配置，可传入不同的 config_file。
    """
    global _global_settings
    if _global_settings is None or config_file is not None:
        _global_settings = Settings(config_file)
    return _global_settings


def reload_settings(config_file: Optional[str] = None) -> Settings:
    """重新加载全局 Settings"""
    global _global_settings
    _global_settings = Settings(config_file)
    return _global_settings
