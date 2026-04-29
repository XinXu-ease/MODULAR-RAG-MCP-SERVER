"""MCP Tool: list_collections - 列出知识库中的集合."""

import logging
from typing import Any, Dict, List, Optional

from src.core.settings import get_settings
from src.libs.vector_store.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class ListCollectionsTool:
    """
    MCP Tool: list_collections
    
    列出向量存储中的所有集合并返回统计信息。
    """

    def __init__(self, vector_store: Optional[ChromaStore] = None):
        """
        初始化工具。

        Args:
            vector_store: 向量存储实例（可为 None，将自动创建）
        """
        self.vector_store = vector_store or ChromaStore()
        self.settings = get_settings()

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        执行列表查询。

        Returns:
            包含集合列表的响应
        """
        try:
            logger.info("Listing collections from vector store")

            # 获取所有集合
            collections = self._get_collections()

            if not collections:
                return {
                    "success": True,
                    "collections": [],
                    "total_collections": 0,
                    "message": "No collections found in the knowledge hub",
                }

            logger.info(f"Found {len(collections)} collections")

            return {
                "success": True,
                "collections": collections,
                "total_collections": len(collections),
            }

        except Exception as e:
            logger.exception(f"Failed to list collections: {e}")
            return self._error_response(f"Internal error: {str(e)}")

    def _get_collections(self) -> List[Dict[str, Any]]:
        """
        获取向量存储中的所有集合。

        Returns:
            集合列表，每个集合包含：
            - name: 集合名称
            - doc_count: 文档数量
            - chunk_count: chunk 数量
            - last_updated: 最后更新时间（可选）
        """
        collections: Dict[str, Dict[str, Any]] = {}

        try:
            # 从ChromaStore获取所有数据
            # Chroma 没有直接列出metadata唯一值的方法，
            # 但我们可以通过查询所有数据来统计
            collection = self.vector_store._collection

            # 获取集合中的所有数据（不提供限制）
            all_data = collection.get(include=["metadatas"])

            if not all_data or "metadatas" not in all_data:
                return []

            # 按 collection 字段分组统计
            for metadata in all_data["metadatas"]:
                if metadata is None:
                    continue

                collection_name = metadata.get("collection", "default")

                if collection_name not in collections:
                    collections[collection_name] = {
                        "name": collection_name,
                        "doc_ids": set(),
                        "chunk_count": 0,
                    }

                # 统计 chunks
                collections[collection_name]["chunk_count"] += 1

                # 统计文档
                doc_id = metadata.get("doc_id", metadata.get("source", "unknown"))
                collections[collection_name]["doc_ids"].add(doc_id)

            # 转换为列表格式
            result = []
            for col_name, col_data in collections.items():
                result.append({
                    "name": col_name,
                    "doc_count": len(col_data["doc_ids"]),
                    "chunk_count": col_data["chunk_count"],
                })

            # 按名称排序
            result.sort(key=lambda x: x["name"])
            return result

        except Exception as e:
            logger.warning(f"Failed to get collections from vector store: {e}")
            # 返回默认集合
            return [{"name": "default", "doc_count": 0, "chunk_count": 0}]

    @staticmethod
    def _error_response(message: str) -> Dict[str, Any]:
        """构建错误响应."""
        return {
            "success": False,
            "collections": [],
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
            "name": "list_collections",
            "description": "List all collections in the knowledge hub with statistics (document count, chunk count).",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }


# Standalone function for MCP integration
async def list_collections() -> Dict[str, Any]:
    """
    MCP Tool 入口函数。

    Returns:
        包含集合列表的响应
    """
    tool = ListCollectionsTool()
    return tool.execute()
