"""Unit tests for get_document_summary tool."""

import pytest
from unittest.mock import MagicMock, patch

from src.mcp_server.tools.get_document_summary import GetDocumentSummaryTool


@pytest.fixture
def mock_settings():
    """Fixture for mocking get_settings."""
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    """Fixture for creating a mock vector store."""
    store = MagicMock()
    return store


class TestGetDocumentSummaryTool:
    """Test GetDocumentSummaryTool."""

    def test_tool_imports(self):
        """Test that tool imports successfully."""
        assert GetDocumentSummaryTool is not None

    def test_tool_schema(self):
        """Test that tool provides valid MCP schema."""
        schema = GetDocumentSummaryTool.to_tool_schema()

        # Validate schema structure
        assert "name" in schema
        assert schema["name"] == "get_document_summary"
        assert "description" in schema
        assert "inputSchema" in schema

        # Validate input schema
        input_schema = schema["inputSchema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "doc_id" in input_schema["properties"]
        assert input_schema["required"] == ["doc_id"]

    def test_execute_empty_doc_id(self, mock_vector_store, mock_settings):
        """Test error handling for empty doc_id."""
        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_execute_doc_not_found(self, mock_vector_store, mock_settings):
        """Test error handling when document not found."""
        mock_vector_store.get_by_ids.return_value = []

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="nonexistent_doc")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_execute_doc_found_complete_metadata(self, mock_vector_store, mock_settings):
        """Test successful retrieval with complete metadata."""
        mock_result = {
            "id": "doc1",
            "metadata": {
                "title": "Sample Document",
                "summary": "This is a sample document summary",
                "tags": ["sample", "document", "test"],
                "source": "test.pdf",
                "page": 1,
                "collection": "test_collection",
                "enriched_by": "llm",
            },
            "text": "Full document content...",
        }
        mock_vector_store.get_by_ids.return_value = [mock_result]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="doc1")

        assert result["success"] is True
        assert result["doc_id"] == "doc1"
        assert result["document"]["title"] == "Sample Document"
        assert result["document"]["summary"] == "This is a sample document summary"
        assert result["document"]["tags"] == ["sample", "document", "test"]
        assert result["document"]["source"] == "test.pdf"
        assert result["document"]["page"] == 1
        assert result["document"]["collection"] == "test_collection"

    def test_execute_doc_found_minimal_metadata(self, mock_vector_store, mock_settings):
        """Test retrieval with minimal metadata (defaults applied)."""
        mock_result = {
            "id": "doc2",
            "metadata": {
                "source": "doc2.txt",
            },
            "text": "Minimal document",
        }
        mock_vector_store.get_by_ids.return_value = [mock_result]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="doc2")

        assert result["success"] is True
        assert result["document"]["title"] == "Untitled"
        assert result["document"]["summary"] == "No summary available"
        assert result["document"]["tags"] == []
        assert result["document"]["source"] == "doc2.txt"
        assert result["document"]["collection"] == "default"

    def test_execute_doc_with_partial_metadata(self, mock_vector_store, mock_settings):
        """Test retrieval with partial metadata."""
        mock_result = {
            "id": "doc3",
            "metadata": {
                "title": "Partial Doc",
                "source": "doc3.pdf",
                # missing: summary, tags, page, collection, enriched_by
            },
            "text": "Partial metadata document",
        }
        mock_vector_store.get_by_ids.return_value = [mock_result]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="doc3")

        assert result["success"] is True
        assert result["document"]["title"] == "Partial Doc"
        assert result["document"]["summary"] == "No summary available"
        assert result["document"]["source"] == "doc3.pdf"
        assert result["document"]["page"] is None
        assert result["document"]["collection"] == "default"

    def test_execute_error_handling(self, mock_vector_store, mock_settings):
        """Test error handling when vector store fails."""
        mock_vector_store.get_by_ids.side_effect = Exception("Vector store error")

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="doc4")

        assert result["success"] is False
        assert "error" in result

    def test_whitespace_doc_id(self, mock_vector_store, mock_settings):
        """Test that whitespace-only doc_id is rejected."""
        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="   ")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_error_response_format(self):
        """Test error response format."""
        error_msg = "Test error"
        response = GetDocumentSummaryTool._error_response(error_msg)

        assert response["success"] is False
        assert response["error"] == error_msg

    def test_doc_id_passed_correctly(self, mock_vector_store, mock_settings):
        """Test that doc_id is passed correctly to vector_store."""
        mock_result = {
            "id": "test_doc_id",
            "metadata": {"source": "test.pdf"},
            "text": "Test",
        }
        mock_vector_store.get_by_ids.return_value = [mock_result]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="test_doc_id")

        # Verify that get_by_ids was called with the correct doc_id
        mock_vector_store.get_by_ids.assert_called_once_with(["test_doc_id"])

    def test_metadata_nested_in_response(self, mock_vector_store, mock_settings):
        """Test that complete metadata is nested in response."""
        mock_metadata = {
            "title": "Test",
            "source": "test.pdf",
            "custom_field": "custom_value",
        }
        mock_result = {
            "id": "doc5",
            "metadata": mock_metadata,
            "text": "Test",
        }
        mock_vector_store.get_by_ids.return_value = [mock_result]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_vector_store)
            result = tool.execute(doc_id="doc5")

        # Verify metadata is preserved
        assert "metadata" in result["document"]
        assert result["document"]["metadata"]["custom_field"] == "custom_value"


class TestGetDocumentSummaryIntegration:
    """Integration tests for get_document_summary."""

    def test_tool_with_mocked_chroma(self, mock_settings):
        """Test tool with realistic ChromaStore mock."""
        mock_store = MagicMock()

        # Simulate realistic Chroma response
        mock_store.get_by_ids.return_value = [
            {
                "id": "knowledge_doc_1",
                "metadata": {
                    "title": "RAG Architecture Guide",
                    "summary": "Comprehensive guide to building RAG systems",
                    "tags": ["rag", "architecture", "guide"],
                    "source": "architecture.pdf",
                    "page": 5,
                    "collection": "knowledge",
                    "enriched_by": "llm",
                },
                "text": "Full document content here...",
            }
        ]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_store)
            result = tool.execute(doc_id="knowledge_doc_1")

        assert result["success"] is True
        assert result["document"]["title"] == "RAG Architecture Guide"
        assert result["document"]["collection"] == "knowledge"
        assert len(result["document"]["tags"]) == 3

    def test_tool_multiple_docs_in_sequence(self, mock_settings):
        """Test querying multiple documents sequentially."""
        mock_store = MagicMock()

        # First query
        mock_store.get_by_ids.return_value = [
            {
                "id": "doc_a",
                "metadata": {"title": "Doc A", "source": "a.pdf"},
                "text": "Content A",
            }
        ]

        with patch('src.mcp_server.tools.get_document_summary.get_settings', return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_store)
            result1 = tool.execute(doc_id="doc_a")

        assert result1["document"]["title"] == "Doc A"

        # Second query
        mock_store.get_by_ids.return_value = [
            {
                "id": "doc_b",
                "metadata": {"title": "Doc B", "source": "b.pdf"},
                "text": "Content B",
            }
        ]

        result2 = tool.execute(doc_id="doc_b")
        assert result2["document"]["title"] == "Doc B"
