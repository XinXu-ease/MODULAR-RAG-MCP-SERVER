"""Unit tests for response builder."""

import pytest

from src.core.response.citation_generator import CitationGenerator
from src.core.response.response_builder import MCPResponse, ResponseBuilder
from src.core.types import Citation, RetrievalResult


class TestCitationGenerator:
    """Test CitationGenerator."""

    def test_generate_citations(self):
        """Test generating citations from retrieval results."""
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="This is the first chunk",
                metadata={"source": "doc1.pdf", "doc_type": "pdf", "page": 1},
                score=0.95,
            ),
            RetrievalResult(
                chunk_id="chunk_2",
                content="This is the second chunk",
                metadata={"source": "doc2.pdf", "doc_type": "pdf", "page": 5},
                score=0.87,
                image_refs=["img_1", "img_2"],
            ),
        ]

        citations = CitationGenerator.generate(results)

        assert len(citations) == 2
        assert citations[0].id == 1
        assert citations[0].chunk_id == "chunk_1"
        assert citations[0].source == "doc1.pdf"
        assert citations[0].page == 1
        assert citations[0].score == 0.95

        assert citations[1].id == 2
        assert citations[1].source == "doc2.pdf"
        assert len(citations[1].image_refs) == 2

    def test_generate_empty_results(self):
        """Test generating citations from empty results."""
        citations = CitationGenerator.generate([])
        assert citations == []

    def test_to_dict_list(self):
        """Test converting citations to dict list."""
        citations = [
            Citation(
                id=1,
                chunk_id="chunk_1",
                source="doc.pdf",
                doc_type="pdf",
                page=1,
                text="Sample text",
                score=0.9,
            )
        ]

        dict_list = CitationGenerator.to_dict_list(citations)

        assert len(dict_list) == 1
        assert dict_list[0]["id"] == 1
        assert dict_list[0]["source"] == "doc.pdf"
        assert dict_list[0]["page"] == 1


class TestResponseBuilder:
    """Test ResponseBuilder."""

    def test_build_with_results(self):
        """Test building response with retrieval results."""
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="This is the first chunk with important information",
                metadata={"source": "doc1.pdf", "doc_type": "pdf", "page": 1},
                score=0.95,
            ),
            RetrievalResult(
                chunk_id="chunk_2",
                content="This is the second chunk",
                metadata={"source": "doc2.md", "doc_type": "markdown", "page": None},
                score=0.87,
            ),
        ]

        response = ResponseBuilder.build(results, query="test query")

        # Check structure
        assert isinstance(response, MCPResponse)
        assert len(response.content) == 1
        assert response.content[0]["type"] == "text"
        assert len(response.citations) == 2

        # Check markdown content
        markdown = response.content[0]["text"]
        assert "[1]" in markdown  # Citation number
        assert "[2]" in markdown
        assert "doc1.pdf" in markdown
        assert "doc2.md" in markdown
        assert "检索结果（共 2 条）" in markdown

    def test_build_empty_results(self):
        """Test building response with no results."""
        response = ResponseBuilder.build([], query="test query")

        assert len(response.content) == 1
        assert "未找到相关文档" in response.content[0]["text"]
        assert response.citations == []

    def test_build_empty_results_custom_message(self):
        """Test building response with custom empty message."""
        custom_msg = "No results found with custom message"
        response = ResponseBuilder.build([], query="test", empty_message=custom_msg)

        assert custom_msg in response.content[0]["text"]

    def test_mcp_response_to_dict(self):
        """Test converting MCP response to dict."""
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="Test content",
                metadata={"source": "doc.pdf", "doc_type": "pdf"},
                score=0.9,
            )
        ]

        response = ResponseBuilder.build(results, query="test")
        response_dict = response.to_dict()

        assert "content" in response_dict
        assert "structuredContent" in response_dict
        assert "citations" in response_dict["structuredContent"]
        assert len(response_dict["structuredContent"]["citations"]) == 1

    def test_markdown_format(self):
        """Test markdown formatting with page numbers and scores."""
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="A" * 500,  # Long content to test truncation
                metadata={"source": "doc.pdf", "doc_type": "pdf", "page": 42},
                score=0.7654,
            )
        ]

        response = ResponseBuilder.build(results, query="test")
        markdown = response.content[0]["text"]

        # Should have citation numbering
        assert "[1]" in markdown
        # Should have source
        assert "doc.pdf" in markdown
        # Should have page number
        assert "Page 42" in markdown
        # Should have score as percentage
        assert "76.54%" in markdown

    def test_long_content_truncation(self):
        """Test that long content is truncated in citations."""
        long_content = "A" * 500
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content=long_content,
                metadata={"source": "doc.pdf", "doc_type": "pdf"},
                score=0.9,
            )
        ]

        response = ResponseBuilder.build(results, query="test")

        # Check that citation text is truncated
        assert len(response.citations[0].text) == 200
        assert response.citations[0].text == long_content[:200]

    def test_with_image_refs(self):
        """Test response building with image references."""
        results = [
            RetrievalResult(
                chunk_id="chunk_1",
                content="Content with images",
                metadata={"source": "doc.pdf", "doc_type": "pdf"},
                score=0.9,
                image_refs=["img_1", "img_2"],
            )
        ]

        response = ResponseBuilder.build(results, query="test")

        assert len(response.citations[0].image_refs) == 2
        assert "img_1" in response.citations[0].image_refs
