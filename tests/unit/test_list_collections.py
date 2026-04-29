"""Unit tests for list_collections tool."""

import pytest
from unittest.mock import MagicMock, patch

from src.mcp_server.tools.list_collections import ListCollectionsTool


@pytest.fixture
def mock_settings():
    """Fixture for mocking get_settings."""
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    """Fixture for creating a mock vector store."""
    store = MagicMock()
    store._collection = MagicMock()
    return store


class TestListCollectionsTool:
    """Test ListCollectionsTool."""

    def test_tool_imports(self):
        """Test that tool imports successfully."""
        assert ListCollectionsTool is not None

    def test_tool_schema(self):
        """Test that tool provides valid MCP schema."""
        schema = ListCollectionsTool.to_tool_schema()

        # Validate schema structure
        assert "name" in schema
        assert schema["name"] == "list_collections"
        assert "description" in schema
        assert "inputSchema" in schema

        # Validate input schema
        input_schema = schema["inputSchema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        # list_collections has no required parameters
        assert input_schema["required"] == []

    def test_execute_empty_collections(self, mock_vector_store, mock_settings):
        """Test execute with no collections."""
        mock_vector_store._collection.get.return_value = {"metadatas": []}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["collections"] == []
        assert result["total_collections"] == 0

    def test_execute_with_single_collection(self, mock_vector_store, mock_settings):
        """Test execute with a single collection."""
        # Mock data with 2 documents, 3 chunks
        metadatas = [
            {"collection": "docs", "source": "doc1.pdf", "doc_id": "doc1"},
            {"collection": "docs", "source": "doc1.pdf", "doc_id": "doc1"},
            {"collection": "docs", "source": "doc2.md", "doc_id": "doc2"},
        ]
        mock_vector_store._collection.get.return_value = {"metadatas": metadatas}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["total_collections"] == 1
        assert len(result["collections"]) == 1

        col = result["collections"][0]
        assert col["name"] == "docs"
        assert col["doc_count"] == 2
        assert col["chunk_count"] == 3

    def test_execute_with_multiple_collections(self, mock_vector_store, mock_settings):
        """Test execute with multiple collections."""
        # Mock data with 2 collections
        metadatas = [
            # docs collection: 2 documents, 3 chunks
            {"collection": "docs", "source": "doc1.pdf", "doc_id": "doc1"},
            {"collection": "docs", "source": "doc1.pdf", "doc_id": "doc1"},
            {"collection": "docs", "source": "doc2.md", "doc_id": "doc2"},
            # wiki collection: 1 document, 2 chunks
            {"collection": "wiki", "source": "wiki.md", "doc_id": "wiki1"},
            {"collection": "wiki", "source": "wiki.md", "doc_id": "wiki1"},
        ]
        mock_vector_store._collection.get.return_value = {"metadatas": metadatas}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["total_collections"] == 2
        assert len(result["collections"]) == 2

        # Check sorted by name
        collections_by_name = {c["name"]: c for c in result["collections"]}

        assert "docs" in collections_by_name
        assert collections_by_name["docs"]["doc_count"] == 2
        assert collections_by_name["docs"]["chunk_count"] == 3

        assert "wiki" in collections_by_name
        assert collections_by_name["wiki"]["doc_count"] == 1
        assert collections_by_name["wiki"]["chunk_count"] == 2

    def test_execute_with_default_collection(self, mock_vector_store, mock_settings):
        """Test execute with chunks missing collection field (use default)."""
        # Mock data where some chunks don't have collection field
        metadatas = [
            {"collection": "docs", "source": "doc1.pdf"},
            {"source": "doc2.pdf"},  # Missing collection field -> default
            {"collection": "docs", "source": "doc1.pdf"},
        ]
        mock_vector_store._collection.get.return_value = {"metadatas": metadatas}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["total_collections"] == 2

        collections_by_name = {c["name"]: c for c in result["collections"]}
        assert "default" in collections_by_name
        assert "docs" in collections_by_name

    def test_execute_with_none_metadatas(self, mock_vector_store, mock_settings):
        """Test execute with None metadatas (skip them)."""
        # Mock data with some None entries
        metadatas = [
            {"collection": "docs", "source": "doc1.pdf"},
            None,
            {"collection": "docs", "source": "doc2.pdf"},
        ]
        mock_vector_store._collection.get.return_value = {"metadatas": metadatas}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["total_collections"] == 1
        assert result["collections"][0]["chunk_count"] == 2

    def test_execute_error_handling(self, mock_vector_store, mock_settings):
        """Test error handling when vector store fails."""
        mock_vector_store._collection.get.side_effect = Exception("Vector store error")

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        # Should still return success with fallback
        assert result["success"] is True

    def test_collections_sorted_by_name(self, mock_vector_store, mock_settings):
        """Test that collections are sorted alphabetically."""
        # Create collections with names that would be out of order
        metadatas = [
            {"collection": "zebra", "source": "z.txt"},
            {"collection": "alpha", "source": "a.txt"},
            {"collection": "beta", "source": "b.txt"},
        ]
        mock_vector_store._collection.get.return_value = {"metadatas": metadatas}

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_vector_store)
            result = tool.execute()

        # Verify sorted order
        names = [c["name"] for c in result["collections"]]
        assert names == ["alpha", "beta", "zebra"]

    def test_error_response(self):
        """Test error response format."""
        error_msg = "Test error"
        response = ListCollectionsTool._error_response(error_msg)

        assert response["success"] is False
        assert response["error"] == error_msg
        assert response["collections"] == []


class TestListCollectionsIntegration:
    """Integration tests for list_collections."""

    def test_tool_with_mocked_chroma(self, mock_settings):
        """Test tool with mocked ChromaStore behavior."""
        # Create a more realistic mock
        mock_store = MagicMock()
        mock_collection = MagicMock()

        # Simulate real Chroma behavior
        mock_collection.get.return_value = {
            "metadatas": [
                {"collection": "knowledge", "source": "faq.pdf", "doc_id": "faq_1"},
                {"collection": "knowledge", "source": "faq.pdf", "doc_id": "faq_1"},
                {"collection": "knowledge", "source": "guide.pdf", "doc_id": "guide_1"},
                {"collection": "api_docs", "source": "api.md", "doc_id": "api_1"},
            ]
        }
        mock_store._collection = mock_collection

        with patch('src.mcp_server.tools.list_collections.get_settings', return_value=mock_settings):
            tool = ListCollectionsTool(vector_store=mock_store)
            result = tool.execute()

        assert result["success"] is True
        assert result["total_collections"] == 2

        # Verify statistics
        collections_by_name = {c["name"]: c for c in result["collections"]}
        assert collections_by_name["knowledge"]["doc_count"] == 2
        assert collections_by_name["knowledge"]["chunk_count"] == 3
        assert collections_by_name["api_docs"]["doc_count"] == 1
        assert collections_by_name["api_docs"]["chunk_count"] == 1
