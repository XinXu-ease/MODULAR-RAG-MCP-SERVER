"""Response builder: 构建 MCP 格式的响应."""

from typing import Any, Dict, List, Optional

from src.core.response.citation_generator import CitationGenerator
from src.core.types import Citation, RetrievalResult


class MCPResponse:
    """MCP 格式的响应对象."""

    def __init__(self, content: List[Dict[str, Any]], citations: Optional[List[Citation]] = None):
        """
        初始化 MCP 响应。

        Args:
            content: 内容数组（符合 MCP 协议）
            citations: 引用列表
        """
        self.content = content
        self.citations = citations or []

    def to_dict(self) -> Dict[str, Any]:
        """
        将响应转换为字典（用于 MCP JSON-RPC 序列化）。

        Returns:
            包含 content 和 structuredContent 的字典
        """
        result = {"content": self.content}

        if self.citations:
            result["structuredContent"] = {
                "citations": CitationGenerator.to_dict_list(self.citations)
            }

        return result


class ResponseBuilder:
    """
    构建 MCP 格式的响应，包含文本内容与引用信息。
    
    根据检索结果生成可读的 Markdown 文本并嵌入 citation 标注。
    """

    @staticmethod
    def build(
        retrieval_results: List[RetrievalResult], query: str, empty_message: Optional[str] = None
    ) -> MCPResponse:
        """
        从检索结果构建 MCP 响应。

        Args:
            retrieval_results: 检索结果列表
            query: 原始查询文本
            empty_message: 无结果时的提示信息

        Returns:
            MCPResponse 对象
        """
        if not retrieval_results:
            empty_msg = (
                empty_message
                or "未找到相关文档。请先使用 ingest 工具摄取数据，或尝试调整查询关键词。"
            )
            return MCPResponse(content=[{"type": "text", "text": empty_msg}], citations=[])

        # 生成引用列表
        citations = CitationGenerator.generate(retrieval_results)

        # 构建 Markdown 响应
        markdown_text = ResponseBuilder._build_markdown(retrieval_results, citations)

        # 构建 MCP 内容数组
        content = [{"type": "text", "text": markdown_text}]

        return MCPResponse(content=content, citations=citations)

    @staticmethod
    def _build_markdown(retrieval_results: List[RetrievalResult], citations: List[Citation]) -> str:
        """
        从检索结果生成 Markdown 格式文本。

        Args:
            retrieval_results: 检索结果
            citations: 引用列表

        Returns:
            Markdown 格式的文本
        """
        lines = []

        # 检索摘要
        lines.append(f"## 检索结果（共 {len(retrieval_results)} 条）\n")

        for result, citation in zip(retrieval_results, citations):
            # 文本片段 + 引用标注
            lines.append(f"### [{citation.id}] {result.metadata.get('source', 'Unknown')}")
            lines.append("")

            # 片段内容
            content_preview = result.content[:300]
            if len(result.content) > 300:
                content_preview += "..."
            lines.append(content_preview)
            lines.append("")

            # 元数据信息（来源、页码、得分）
            meta_parts = []
            if citation.page is not None:
                meta_parts.append(f"📄 Page {citation.page}")
            meta_parts.append(f"📊 Score: {result.score:.2%}")
            if result.metadata.get("doc_type"):
                meta_parts.append(f"🏷️ Type: {result.metadata['doc_type']}")

            if meta_parts:
                lines.append(f"__{' | '.join(meta_parts)}__")
            lines.append("")

        # 引用列表
        lines.append("---")
        lines.append("## 引用来源\n")
        for citation in citations:
            lines.append(
                f"[{citation.id}] **{citation.source}** (Score: {citation.score:.2%})"
            )
            if citation.page is not None:
                lines.append(f"   - Page: {citation.page}")

        return "\n".join(lines)
