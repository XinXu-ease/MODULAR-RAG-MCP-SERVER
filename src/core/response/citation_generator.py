"""Citation generator: 从检索结果生成引用信息."""

from typing import Dict, List, Optional

from src.core.types import Citation, RetrievalResult


class CitationGenerator:
    """
    从检索结果生成结构化的引用信息。
    
    将检索结果转换为可追踪的引用列表，包含来源、页码、相关性分数等信息。
    """

    @staticmethod
    def generate(retrieval_results: List[RetrievalResult]) -> List[Citation]:
        """
        从检索结果列表生成引用列表。

        Args:
            retrieval_results: 检索结果列表

        Returns:
            Citation 对象列表，按原顺序编号
        """
        citations: List[Citation] = []

        for idx, result in enumerate(retrieval_results, start=1):
            source = result.metadata.get("source", "unknown")
            doc_type = result.metadata.get("doc_type", "document")
            page = result.metadata.get("page", None)
            image_refs = result.image_refs or []

            citation = Citation(
                id=idx,
                chunk_id=result.chunk_id,
                source=source,
                doc_type=doc_type,
                page=page,
                text=result.content[:200],  # 截断到200字符作为摘要
                score=result.score,
                image_refs=image_refs,
            )
            citations.append(citation)

        return citations

    @staticmethod
    def to_dict_list(citations: List[Citation]) -> List[Dict]:
        """
        将 Citation 对象列表转换为字典列表（用于序列化）。

        Args:
            citations: Citation 对象列表

        Returns:
            字典列表
        """
        return [
            {
                "id": c.id,
                "chunk_id": c.chunk_id,
                "source": c.source,
                "doc_type": c.doc_type,
                "page": c.page,
                "text": c.text,
                "score": c.score,
                "image_refs": c.image_refs,
            }
            for c in citations
        ]
