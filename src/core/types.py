"""
Core Data Types & Contracts

定义整个 RAG 系统的核心数据结构，确保各模块间的类型一致性。
这些类型贯穿 Ingestion Pipeline 与 Retrieval 两条链路。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class Document:
    """
    通用的文档对象，Loader 层的输出标准格式。
    
    所有 Loader（PDF/Website/Markdown）都必须输出统一的 Document 结构，
    后续 Splitter/Transform/Embed 等模块依赖该标准格式。
    """
    
    id: str  # 文档唯一标识（通常为源文件路径的哈希）
    text: str  # 规范化为 Markdown 格式的文档正文
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """基础校验"""
        if not self.id:
            raise ValueError("Document.id 不能为空")
        if not self.text:
            raise ValueError("Document.text 不能为空")
        # 确保必有的基础 metadata 字段
        if "source" not in self.metadata:
            raise ValueError("Document.metadata 必须包含 'source' 字段")


@dataclass
class Chunk:
    """
    切分后的文本片段，Splitter 和 Transform 层的核心数据结构。
    
    每个 Chunk 代表一个语义完整的片段，包含原文本、定位信息、元数据。
    """
    
    id: str  # Chunk 唯一标识（通常为 hash(source + section_path + content_hash)）
    content: str  # Chunk 的文本内容（可能包含图片描述、元数据等增强信息）
    
    # 定位与来源信息
    source: str  # 原始文件路径或 URL
    chunk_index: int  # 该文档内的 chunk 顺序号（0-based）
    start_offset: Optional[int] = None  # 在原文档中的起始位置
    end_offset: Optional[int] = None  # 在原文档中的结束位置
    
    # 元数据（由 Loader 初始化，Splitter/Transform 逐步丰富）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 图片引用（Transform 阶段可能增加）
    image_refs: List[str] = field(default_factory=list)  # 关联的图片 ID 列表


@dataclass
class ChunkRecord:
    """
    向量库存储的完整记录，包含向量、正文、元数据。
    
    这是 Embedding 和 Upsert 阶段的输出，代表一个完整的可索引记录。
    """
    
    id: str  # 唯一标识，与 Chunk.id 一致，用于幂等更新
    content: str  # 完整的 Chunk 正文
    
    # 向量表示（双路编码）
    dense_embedding: Optional[List[float]] = None  # Dense 向量（语义）
    sparse_embedding: Optional[Dict[str, float]] = None  # Sparse 向量（关键词权重）
    
    # 元数据（原样存储）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # 额外信息
    chunk_hash: str = ""  # 内容哈希，用于检测重复
    image_refs: List[str] = field(default_factory=list)  # 关联的图片 ID


@dataclass
class RetrievalResult:
    """
    检索的单个结果项，包含文档片段与相关信息。
    """
    
    chunk_id: str  # 被检索的 Chunk ID
    content: str  # 片段正文
    metadata: Dict[str, Any]  # 元数据（source, page, doc_type 等）
    score: float  # 相关性分数（0-1）
    score_breakdown: Optional[Dict[str, float]] = None  # 分数细节（dense, sparse, rerank）
    image_refs: List[str] = field(default_factory=list)  # 关联的图片


@dataclass
class QueryResult:
    """
    一次检索的完整结果。包含查询文本、Top-K 片段、引用信息。
    """
    
    query: str  # 原始查询
    retrieved_chunks: List[RetrievalResult]  # Top-K 检索结果
    total_latency_ms: float  # 端到端耗时（毫秒）
    
    # 分阶段耗时
    stage_latencies: Dict[str, float] = field(default_factory=dict)
    
    # 元数据
    trace_id: Optional[str] = None  # 关联的 Trace ID
    retrieval_method: str = "hybrid"  # 使用的检索方法（dense/sparse/hybrid）
    rerank_method: Optional[str] = None  # 使用的重排方法（none/cross_encoder/llm）


@dataclass
class Citation:
    """
    引用信息，指向一个检索结果的完整定位。
    """
    
    id: int  # 在答案中的引用序号
    chunk_id: str  # 被引用的 Chunk ID
    source: str  # 来源文件名或 URL
    doc_type: str  # 文档类型（pdf/website）
    page: Optional[int] = None  # 页码（对 PDF）
    text: str = ""  # 被引用的原文片段
    score: float = 0.0  # 相关性分数
    
    # 额外信息
    image_refs: List[str] = field(default_factory=list)  # 关联的图片


# ============================================================================
# Ingestion 相关类型
# ============================================================================

@dataclass
class IngestionMetrics:
    """数据摄取的统计指标"""
    
    total_chunks: int = 0  # 处理的 Chunk 总数
    total_images: int = 0  # 处理的图片总数
    skipped_chunks: int = 0  # 跳过的 Chunk（已存在）
    failed_chunks: int = 0  # 失败的 Chunk
    total_latency_ms: float = 0.0  # 总耗时


@dataclass
class IngestionResult:
    """一次数据摄取的结果"""
    
    success: bool  # 是否成功
    source: str  # 源文件
    metrics: IngestionMetrics  # 统计指标
    error: Optional[str] = None  # 错误信息（若失败）
    trace_id: Optional[str] = None  # 关联的 Trace ID


# ============================================================================
# Settings 与配置相关类型（将在 settings.py 中使用）
# ============================================================================

@dataclass
class LLMConfig:
    """LLM 提供者配置"""
    provider: str  # azure | openai | ollama | deepseek
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    deployment_name: Optional[str] = None  # For Azure


@dataclass
class EmbeddingConfig:
    """Embedding 提供者配置"""
    provider: str  # openai | bgE | ollama
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    dimension: int = 1536  # 向量维度


@dataclass
class VectorStoreConfig:
    """向量库配置"""
    backend: str  # chroma | qdrant | pinecone
    persist_directory: str = "data/db/chroma"


@dataclass
class RetrievalConfig:
    """检索策略配置"""
    top_k: int = 10  # 默认返回 Top-K
    sparse_backend: str = "bm25"  # 稀疏检索后端
    fusion_algorithm: str = "rrf"  # 融合算法
    rerank_backend: Optional[str] = None  # None | cross_encoder | llm


# ============================================================================
# 辅助工具函数
# ============================================================================

def validate_document(doc: Document) -> bool:
    """验证 Document 的基本合法性"""
    required_metadata = {"source"}
    if not all(k in doc.metadata for k in required_metadata):
        return False
    if not doc.text.strip():
        return False
    return True


def validate_chunk(chunk: Chunk) -> bool:
    """验证 Chunk 的基本合法性"""
    if not chunk.id or not chunk.content.strip():
        return False
    if chunk.chunk_index < 0:
        return False
    return True
