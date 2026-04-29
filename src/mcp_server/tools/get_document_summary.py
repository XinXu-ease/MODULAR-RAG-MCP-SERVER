"""MCP Tool: get_document_summary - 获取文档摘要."""

import logging
from typing import Any, Dict, List, Optional

from src.core.settings import get_settings
from src.libs.vector_store.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class GetDocumentSummaryTool:
    """
    MCP Tool: get_document_summary
    
    按文档 ID 查询向量存储并返回文档的摘要信息（title、summary、tags 等）。
    """

    def __init__(self, vector_store: Optional[ChromaStore] = None):
        """
        初始化工具。

        Args:
            vector_store: 向量存储实例（可为 None，将自动创建）
        """
        self.vector_store = vector_store or ChromaStore()
        self.settings = get_settings()

    def execute(self, doc_id: str, **kwargs: Any) -> Dict[str, Any]:
        """
        执行文档查询。

        Args:
            doc_id: 文档 ID
            **kwargs: 其他参数

        Returns:
            包含文档摘要信息的响应
        """
        try:
            # 参数验证
            if not doc_id or not doc_id.strip():
                return self._error_response("doc_id cannot be empty")

            logger.info(f"Getting document summary for doc_id='{doc_id}'")

            # 查询文档
            document = self._get_document(doc_id)

            if not document:
                return self._error_response(f"Document '{doc_id}' not found")

            logger.info(f"Found document '{doc_id}' with metadata")

            return {
                "success": True,
                "doc_id": doc_id,
                "document": document,
            }

        except Exception as e:
            logger.exception(f"Failed to get document summary: {e}")
            return self._error_response(f"Internal error: {str(e)}")

    def _get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        从向量存储中查询单个文档信息。

        Args:
            doc_id: 文档 ID

        Returns:
            文档信息（包含 title、summary、tags、source 等），如果不存在返回 None
        """
        try:
            # 使用 ChromaStore 的 get_by_ids 方法
            results = self.vector_store.get_by_ids([doc_id])

            if not results or len(results) == 0:
                return None

            result = results[0]
            metadata = result.get("metadata", {})

            # 构建文档摘要信息
            document_info = {
                "id": doc_id,
                "title": metadata.get("title", "Untitled"),
                "summary": metadata.get("summary", "No summary available"),
                "tags": metadata.get("tags", []),
                "source": metadata.get("source", "Unknown"),
                "page": metadata.get("page"),  # 可能为 None
                "collection": metadata.get("collection", "default"),
                "enriched_by": metadata.get("enriched_by", "unknown"),
            }

            # 如果有更多元数据，可以添加
            document_info["metadata"] = metadata

            return document_info

        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            return None

    @staticmethod
    def to_tool_schema() -> Dict[str, Any]:
        """
        返回 MCP tool schema。

        Returns:
            符合 MCP 规范的 tool 定义
        """
        return {
            "name": "get_document_summary",
            "description": "Get summary information for a document by ID. Returns title, summary, tags, and other metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document ID to retrieve",
                    },
                },
                "required": ["doc_id"],
            },
        }

    @staticmethod
    def _error_response(error_msg: str) -> Dict[str, Any]:
        """
        返回标准错误响应。

        Args:
            error_msg: 错误信息

        Returns:
            错误响应字典
        """
        return {
            "success": False,
            "error": error_msg,
        }


# Standalone function for MCP integration
async def get_document_summary(doc_id: str) -> Dict[str, Any]:
    """
    MCP Tool 入口函数。

    Args:
        doc_id: 文档 ID

    Returns:
        包含文档摘要信息的响应
    """
    tool = GetDocumentSummaryTool()
    return tool.execute(doc_id=doc_id)
