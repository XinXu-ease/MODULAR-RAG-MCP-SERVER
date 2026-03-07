#!/usr/bin/env python
"""
Smart Knowledge Hub - Entry Point

Minimal runnable entry point for Phase A verification.
"""

import sys
import logging
from pathlib import Path

# 将 src 目录加入 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from core.settings import get_settings
from core.types import Document

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def verify_project_structure():
    """验证项目结构与基础功能"""
    logger.info("=" * 60)
    logger.info("Smart Knowledge Hub - Phase A Verification")
    logger.info("=" * 60)
    
    # 1. 验证配置加载
    logger.info("\n[1/3] Loading configuration...")
    try:
        settings = get_settings()
        logger.info(f"✓ Configuration loaded successfully")
        logger.info(f"  - LLM Provider: {settings.llm.provider} ({settings.llm.model})")
        logger.info(f"  - Embedding Provider: {settings.embedding.provider} ({settings.embedding.model})")
        logger.info(f"  - Vector Store: {settings.vector_store.backend}")
    except Exception as e:
        logger.error(f"✗ Configuration loading failed: {e}")
        return False
    
    # 2. 验证核心数据类型
    logger.info("\n[2/3] Testing core data types...")
    try:
        # 测试 Document 创建
        doc = Document(
            id="test_doc_1",
            text="This is a test document.",
            metadata={"source": "test.txt", "doc_type": "text"}
        )
        logger.info(f"✓ Document created: {doc.id[:30]}...")
    except Exception as e:
        logger.error(f"✗ Document creation failed: {e}")
        return False
    
    # 3. 验证目录结构
    logger.info("\n[3/3] Verifying directory structure...")
    required_dirs = [
        "src", "src/core", "src/mcp_server", "src/ingestion",
        "src/libs", "src/observability",
        "tests", "tests/unit", "tests/integration", "tests/e2e",
        "config", "data", "data/db", "data/images", "data/logs"
    ]
    
    missing_dirs = []
    for d in required_dirs:
        dir_path = project_root / d
        if not dir_path.exists():
            missing_dirs.append(d)
            logger.warning(f"✗ Missing: {d}")
        else:
            logger.info(f"✓ Found: {d}")
    
    if missing_dirs:
        logger.error(f"Missing directories: {missing_dirs}")
        return False
    
    # 最终总结
    logger.info("\n" + "=" * 60)
    logger.info("✓ Phase A Verification PASSED")
    logger.info("=" * 60)
    logger.info("""
Next Steps (Phase B):
  1. Implement LLM Factory & Base Classes
  2. Implement Embedding Factory
  3. Implement Splitter Factory
  4. Implement VectorStore Factory
  5. ... and other pluggable components
""")
    return True


if __name__ == "__main__":
    success = verify_project_structure()
    sys.exit(0 if success else 1)
