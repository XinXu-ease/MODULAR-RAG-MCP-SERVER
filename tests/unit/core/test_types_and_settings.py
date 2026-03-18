"""
Unit Tests for Core Module (types.py, settings.py)

验证核心数据类型与配置系统的正确性。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.types import (
    Document, Chunk, ChunkRecord, RetrievalResult, QueryResult,
    Citation, IngestionMetrics, IngestionResult,
    validate_document, validate_chunk,
)
from src.core.settings import Settings, get_settings, reload_settings


# ============================================================================
# Tests for types.py
# ============================================================================

class TestDocument:
    """Document 类型的单元测试"""
    
    def test_document_creation(self):
        """测试 Document 创建"""
        doc = Document(
            id="doc_1",
            text="Sample document text",
            metadata={"source": "test.txt", "doc_type": "text"}
        )
        assert doc.id == "doc_1"
        assert doc.text == "Sample document text"
        assert doc.metadata["source"] == "test.txt"
    
    def test_document_missing_id(self):
        """测试缺少 ID 时的验证"""
        with pytest.raises(ValueError):
            Document(
                id="",  # 空 ID
                text="Text",
                metadata={"source": "test.txt"}
            )
    
    def test_document_missing_source_metadata(self):
        """测试缺少 source 元数据时的验证"""
        with pytest.raises(ValueError):
            Document(
                id="doc_1",
                text="Text",
                metadata={}  # 缺少 source
            )
    
    def test_validate_document(self):
        """测试 validate_document 函数"""
        # 有效的 Document
        valid_doc = Document(
            id="doc_1",
            text="Content",
            metadata={"source": "file.txt"}
        )
        assert validate_document(valid_doc) is True
        
        # 无效的 Document（空文本）
        # 注意：Document 创建时会在 __post_init__ 验证 source 字段，
        # 所以这里我们测试空文本的验证
        valid_doc_empty_text = Document(
            id="doc_2",
            text="   ",  # 只有空格
            metadata={"source": "file.txt"}
        )
        # validate_document 应该返回 False（文本为空）
        assert validate_document(valid_doc_empty_text) is False


class TestChunk:
    """Chunk 类型的单元测试"""
    
    def test_chunk_creation(self):
        """测试 Chunk 创建"""
        chunk = Chunk(
            id="chunk_1",
            content="Chunk content",
            source="doc_1",
            chunk_index=0,
            metadata={"page": 1},
        )
        assert chunk.id == "chunk_1"
        assert chunk.content == "Chunk content"
        assert chunk.chunk_index == 0
        assert chunk.metadata["page"] == 1
    
    def test_chunk_image_refs(self):
        """测试 Chunk 的图片引用"""
        chunk = Chunk(
            id="chunk_1",
            content="Content with image",
            source="doc_1",
            chunk_index=0,
            image_refs=["img_1", "img_2"]
        )
        assert len(chunk.image_refs) == 2
        assert "img_1" in chunk.image_refs
    
    def test_validate_chunk(self):
        """测试 validate_chunk 函数"""
        valid_chunk = Chunk(
            id="chunk_1",
            content="Valid content",
            source="doc_1",
            chunk_index=0,
        )
        assert validate_chunk(valid_chunk) is True
        
        # 无效 chunk（chunk_index < 0）
        invalid_chunk = Chunk(
            id="chunk_2",
            content="Content",
            source="doc_1",
            chunk_index=-1,
        )
        assert validate_chunk(invalid_chunk) is False


class TestChunkRecord:
    """ChunkRecord 类型的单元测试"""
    
    def test_chunk_record_creation(self):
        """测试 ChunkRecord 创建"""
        record = ChunkRecord(
            id="chunk_1",
            content="Content",
            dense_embedding=[0.1, 0.2, 0.3],
            sparse_embedding={"word1": 0.8, "word2": 0.5},
            metadata={"source": "doc_1"},
        )
        assert record.id == "chunk_1"
        assert len(record.dense_embedding) == 3
        assert "word1" in record.sparse_embedding


class TestRetrievalResult:
    """RetrievalResult 类型的单元测试"""
    
    def test_retrieval_result_creation(self):
        """测试 RetrievalResult 创建"""
        result = RetrievalResult(
            chunk_id="chunk_1",
            content="Retrieved content",
            metadata={"source": "doc_1", "page": 5},
            score=0.95,
        )
        assert result.chunk_id == "chunk_1"
        assert result.score == 0.95


class TestQueryResult:
    """QueryResult 类型的单元测试"""
    
    def test_query_result_creation(self):
        """测试 QueryResult 创建"""
        retrieved = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="Content 1",
                metadata={"source": "doc_1"},
                score=0.95,
            )
        ]
        result = QueryResult(
            query="test query",
            retrieved_chunks=retrieved,
            total_latency_ms=100.5,
        )
        assert result.query == "test query"
        assert len(result.retrieved_chunks) == 1


# ============================================================================
# Tests for settings.py
# ============================================================================

class TestSettings:
    """Settings 类的单元测试"""
    
    def test_settings_default_values(self):
        """测试 Settings 的默认值"""
        settings = Settings()
        
        # 检验默认 LLM 配置（与 Settings._defaults 保持一致）
        assert settings.llm.provider == "openai"
        assert settings.llm.model == "gpt-4"
        
        # 检验默认 Embedding 配置
        assert settings.embedding.provider == "openai"
        
        # 检验默认向量库
        assert settings.vector_store.backend == "chroma"
    
    def test_settings_llm_config(self):
        """测试 LLM 配置访问"""
        settings = Settings()
        llm = settings.llm
        
        assert llm.provider is not None
        assert llm.model is not None
    
    def test_settings_embedding_config(self):
        """测试 Embedding 配置访问"""
        settings = Settings()
        emb = settings.embedding
        
        assert emb.provider is not None
        assert emb.model is not None
        assert emb.dimension > 0
    
    def test_settings_retrieval_config(self):
        """测试检索配置访问"""
        settings = Settings()
        ret = settings.retrieval
        
        assert ret.top_k > 0
        assert ret.fusion_algorithm is not None
    
    def test_settings_to_dict(self):
        """测试导出为字典"""
        settings = Settings()
        config_dict = settings.to_dict()
        
        assert "llm" in config_dict
        assert "embedding" in config_dict
        assert "vector_store" in config_dict
    
    def test_settings_find_config_file(self):
        """测试配置文件查找"""
        # 这个测试依赖于文件系统
        config_file = Settings._find_config_file()
        # 由于项目初期可能没有 settings.yaml，所以可能返回 None
        # 这个测试只是确保函数能正常执行
        assert config_file is None or isinstance(config_file, str)
    
    def test_settings_get_method(self):
        """测试通用 get 方法"""
        settings = Settings()
        
        # 测试一级访问
        assert settings.get("llm") is not None
        
        # 测试点号路径访问（暂时不支持，但可以测试返回默认值）
        result = settings.get("unknown_key", "default_value")
        assert result == "default_value"
    
    def test_get_settings_singleton(self):
        """测试 get_settings 单例行为"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # 应该返回同一实例
        assert settings1 is settings2
    
    def test_reload_settings(self):
        """测试 reload_settings 函数"""
        settings1 = get_settings()
        settings2 = reload_settings()
        
        # reload 应该创建新实例
        assert settings1 is not settings2


class TestSettingsWithYAML:
    """Settings 与 YAML 配置文件集成测试"""
    
    def test_load_yaml_config(self, tmp_path):
        """测试加载 YAML 配置文件"""
        import tempfile
        
        # 创建临时 YAML 配置
        config_content = """
llm:
  provider: openai
  model: gpt-4
  api_key: test_key

embedding:
  provider: openai
  model: text-embedding-3-small
"""
        
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(config_content)
        
        # 加载配置
        settings = Settings(str(config_file))
        
        assert settings.llm.provider == "openai"
        assert settings.llm.model == "gpt-4"
        assert settings.embedding.provider == "openai"
    
    def test_load_json_config(self, tmp_path):
        """测试加载 JSON 配置文件"""
        import json
        
        config_data = {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
            }
        }
        
        config_file = tmp_path / "settings.json"
        config_file.write_text(json.dumps(config_data))
        
        settings = Settings(str(config_file))
        assert settings.llm.provider == "deepseek"


# ============================================================================
# Integration Tests (简单的集成测试)
# ============================================================================

class TestCoreIntegration:
    """核心模块的集成测试"""
    
    def test_document_to_chunk_workflow(self):
        """测试从 Document 到 Chunk 的工作流"""
        # 创建 Document
        doc = Document(
            id="doc_1",
            text="This is a test document with multiple chunks.",
            metadata={"source": "test.pdf", "doc_type": "pdf"}
        )
        
        # 创建关联的 Chunk
        chunk = Chunk(
            id="chunk_1",
            content=doc.text,
            source=doc.metadata["source"],
            chunk_index=0,
            metadata={"page": 1}
        )
        
        assert chunk.source == "test.pdf"
        assert validate_document(doc) is True
        assert validate_chunk(chunk) is True
    
    def test_chunk_record_workflow(self):
        """测试 Chunk → ChunkRecord 的工作流"""
        chunk = Chunk(
            id="chunk_1",
            content="Sample content",
            source="doc_1",
            chunk_index=0,
        )
        
        # 转换为 ChunkRecord（可用于存储）
        record = ChunkRecord(
            id=chunk.id,
            content=chunk.content,
            dense_embedding=[0.1] * 100,
            metadata={"source": chunk.source},
        )
        
        assert record.id == chunk.id
        assert record.content == chunk.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
