"""
PyTest Configuration & Fixtures

为整个项目提供全局的测试配置与共享 fixtures。
"""

import sys
import os
from pathlib import Path

import pytest

# 将 src 目录加入 Python 路径，使得 import src.* 能够正常工作
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


# ============================================================================
# 全局 PyTest 配置
# ============================================================================

def pytest_configure(config):
    """PyTest 启动时的全局配置"""
    # 标记自定义标记（用于分类测试）
    config.addinivalue_line(
        "markers", "unit: unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: slow running tests"
    )


# ============================================================================
# 共享 Fixtures
# ============================================================================

@pytest.fixture
def test_data_dir() -> Path:
    """测试数据目录"""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(exist_ok=True, parents=True)
    return data_dir


@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """临时数据库路径"""
    return tmp_path / "test_db"


@pytest.fixture
def sample_settings():
    """示例配置（用于测试）"""
    from src.core.settings import Settings
    
    # 返回一个最小化的可测试配置
    settings = Settings()
    return settings


@pytest.fixture
def mock_llm_client(mocker):
    """Mock LLM Client（用于单元测试）"""
    from unittest.mock import Mock
    
    mock = Mock()
    mock.chat.return_value = "Mock LLM response"
    return mock


@pytest.fixture
def mock_embedding_client(mocker):
    """Mock Embedding Client"""
    from unittest.mock import Mock
    
    mock = Mock()
    # 返回一个固定维度的向量
    mock.embed.return_value = [[0.1] * 1536 for _ in range(10)]
    return mock


# ============================================================================
# Marker 函数 (便捷装饰器)
# ============================================================================

def pytest_runtest_setup(item):
    """在每个测试运行前的设置"""
    # 可以在这里添加全局的前置处理
    pass
