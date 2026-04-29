"""MCP Tool: query_knowledge_hub - 查询知识库."""

import logging
from typing import Any, Dict, List, Optional

from src.core.query_engine.hybrid_search import HybridSearch
from src.core.query_engine.reranker import Reranker
from src.core.response.response_builder import MCPResponse, ResponseBuilder
from src.core.settings import get_settings
from src.core.trace import TraceContext
from src.core.types import RetrievalResult

logger = logging.getLogger(__name__)


class QueryKnowledgeHubTool:
    """
    MCP Tool: query_knowledge_hub
    
    调用混合搜索和重排引擎，查询知识库并返回结构化结果。
    """

    def __init__(
        self,
        hybrid_search: Optional[HybridSearch] = None,
        reranker: Optional[Reranker] = None,
    ):
        """
        初始化工具。

        Args:
            hybrid_search: 混合搜索引擎（可为 None，将自动创建）
            reranker: 重排引擎（可为 None，将自动创建）
        """
        self.hybrid_search = hybrid_search or HybridSearch()
        self.reranker = reranker or Reranker()
        self.settings = get_settings()

    def execute(
        self, query: str, top_k: int = 5, collection: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        执行查询。

        Args:
            query: 查询文本
            top_k: 返回结果数量（默认 5）
            collection: 集合名称（可选）
            **kwargs: 其他参数

        Returns:
            MCP 格式的响应
        """
        trace = TraceContext(trace_type="query")

        try:
            # 参数验证
            if not query or not query.strip():
                return self._error_response("Query cannot be empty")

            if top_k < 1 or top_k > 50:
                return self._error_response("top_k must be between 1 and 50")

            logger.info(f"Query knowledge hub: query='{query}', top_k={top_k}, collection={collection}")

            # 执行混合搜索
            query_result = self.hybrid_search.search(
                query=query, top_k=top_k, use_rerank=True, trace=trace
            )

            # 获取检索结果
            retrieval_results: List[RetrievalResult] = query_result.retrieved_chunks

            # 过滤集合（如果指定）
            if collection:
                retrieval_results = [
                    r for r in retrieval_results if r.metadata.get("collection") == collection
                ]

            # 构建 MCP 响应
            mcp_response = ResponseBuilder.build(retrieval_results, query)

            # 记录 trace
            trace.record_stage(
                "response_building",
                result_count=len(retrieval_results),
                total_latency=query_result.total_latency_ms,
            )
            trace.finish()

            logger.info(
                f"Query completed successfully: {len(retrieval_results)} results "
                f"in {query_result.total_latency_ms:.0f}ms"
            )

            return {
                "success": True,
                "content": mcp_response.content,
                "structuredContent": mcp_response.to_dict().get("structuredContent", {}),
            }

        except Exception as e:
            logger.exception(f"Query execution failed: {e}")
            return self._error_response(f"Internal error: {str(e)}")

    @staticmethod
    def _error_response(message: str) -> Dict[str, Any]:
        """构建错误响应."""
        return {
            "success": False,
            "content": [{"type": "text", "text": f"❌ Error: {message}"}],
            "error": message,
        }

    @staticmethod
    def to_tool_schema() -> Dict[str, Any]:
        """
        返回 MCP tool schema。

        Returns:
            符合 MCP 规范的 tool 定义
        """
        return {
            "name": "query_knowledge_hub",
            "description": "Query the knowledge hub with a question. Returns relevant document chunks with citations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5, max: 50)",
                        "default": 5,
                    },
                    "collection": {
                        "type": "string",
                        "description": "Filter results to a specific collection (optional)",
                    },
                },
                "required": ["query"],
            },
        }


# Standalone function for MCP integration
async def query_knowledge_hub(
    query: str, top_k: int = 5, collection: Optional[str] = None
) -> Dict[str, Any]:
    """
    MCP Tool 入口函数。

    Args:
        query: 查询文本
        top_k: 返回结果数量
        collection: 集合名称

    Returns:
        MCP 格式的响应
    """
    tool = QueryKnowledgeHubTool()
    return tool.execute(query=query, top_k=top_k, collection=collection)
