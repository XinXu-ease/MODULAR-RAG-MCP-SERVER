"""Unit tests for get_document_summary tool."""

from unittest.mock import MagicMock, patch

from src.mcp_server.tools.get_document_summary import GetDocumentSummaryTool


def _record(
    vector_id: str,
    *,
    chunk_id: str,
    source_ref: str,
    chunk_index: int,
    text: str,
    collection: str = "knowledge",
    title: str = "RAG Architecture Guide",
    source: str = "architecture.pdf",
):
    return {
        "id": vector_id,
        "metadata": {
            "chunk_id": chunk_id,
            "source_ref": source_ref,
            "source": source,
            "title": title,
            "summary": "Comprehensive guide to building RAG systems",
            "tags": ["rag", "architecture"],
            "doc_type": "pdf",
            "collection": collection,
            "chunk_index": chunk_index,
        },
        "text": text,
    }


class TestGetDocumentSummaryTool:
    def test_tool_imports(self):
        assert GetDocumentSummaryTool is not None

    def test_tool_schema_accepts_source_ref_or_chunk_id(self):
        schema = GetDocumentSummaryTool.to_tool_schema()

        assert schema["name"] == "get_document_summary"
        input_schema = schema["inputSchema"]
        assert input_schema["type"] == "object"
        assert "doc_id" in input_schema["properties"]
        assert "source_ref" in input_schema["properties"]
        assert "chunk_id" in input_schema["properties"]
        assert "context_window" in input_schema["properties"]
        assert input_schema["required"] == []

    def test_execute_rejects_empty_lookup(self):
        tool = GetDocumentSummaryTool(vector_store=MagicMock())

        result = tool.execute(doc_id="")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_execute_doc_not_found(self):
        mock_store = MagicMock()
        mock_store.get_by_ids.return_value = []
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(doc_id="nonexistent_doc")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_resolves_source_ref_and_returns_bounded_same_source_window(self):
        mock_store = MagicMock()
        mock_store.list_records.return_value = [
            _record("v0", chunk_id="chunk-0", source_ref="doc-a", chunk_index=0, text="A0"),
            _record("v1", chunk_id="chunk-1", source_ref="doc-a", chunk_index=1, text="A1"),
            _record("v2", chunk_id="chunk-2", source_ref="doc-a", chunk_index=2, text="A2"),
            _record("v3", chunk_id="chunk-3", source_ref="doc-a", chunk_index=3, text="A3"),
            _record("v4", chunk_id="chunk-4", source_ref="doc-b", chunk_index=0, text="B0"),
        ]
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(source_ref="doc-a", context_window=1)

        assert result["success"] is True
        document = result["document"]
        assert document["id"] == "doc-a"
        assert document["source_ref"] == "doc-a"
        assert document["chunk_count"] == 4
        assert document["returned_chunk_count"] == 2
        assert [chunk["chunk_id"] for chunk in document["chunks"]] == ["chunk-0", "chunk-1"]
        assert document["chunk_window"] == {"start_index": 0, "end_index": 1, "total_chunks": 4}

    def test_resolves_chunk_id_and_returns_neighboring_chunks(self):
        mock_store = MagicMock()
        mock_store.list_records.return_value = [
            _record("v0", chunk_id="chunk-0", source_ref="doc-a", chunk_index=0, text="A0"),
            _record("v1", chunk_id="chunk-1", source_ref="doc-a", chunk_index=1, text="A1"),
            _record("v2", chunk_id="chunk-2", source_ref="doc-a", chunk_index=2, text="A2"),
            _record("v3", chunk_id="chunk-3", source_ref="doc-a", chunk_index=3, text="A3"),
            _record("v4", chunk_id="chunk-4", source_ref="doc-a", chunk_index=4, text="A4"),
        ]
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(chunk_id="chunk-2", context_window=1)

        assert result["success"] is True
        document = result["document"]
        assert document["anchor"]["chunk_id"] == "chunk-2"
        assert document["anchor"]["chunk_index"] == 2
        assert [chunk["chunk_id"] for chunk in document["chunks"]] == ["chunk-1", "chunk-2", "chunk-3"]
        assert document["chunk_window"] == {"start_index": 1, "end_index": 3, "total_chunks": 5}

    def test_filters_by_collection(self):
        mock_store = MagicMock()
        mock_store.list_records.return_value = [
            _record(
                "v0",
                chunk_id="chunk-0",
                source_ref="doc-a",
                chunk_index=0,
                text="A0",
                collection="knowledge",
            ),
            _record(
                "v1",
                chunk_id="chunk-1",
                source_ref="doc-a",
                chunk_index=1,
                text="A1",
                collection="other",
            ),
        ]
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(source_ref="doc-a", collection="knowledge")

        assert result["success"] is True
        assert result["document"]["chunk_count"] == 1
        assert result["document"]["collection"] == "knowledge"

    def test_falls_back_to_get_by_ids_for_legacy_vector_store(self):
        mock_store = MagicMock()
        mock_store.get_by_ids.return_value = [
            {
                "id": "legacy-id",
                "metadata": {
                    "title": "Legacy Document",
                    "source": "legacy.pdf",
                    "collection": "default",
                    "chunk_id": "legacy-id",
                    "chunk_index": 0,
                },
                "text": "Legacy content",
            }
        ]
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(doc_id="legacy-id")

        assert result["success"] is True
        assert result["document"]["title"] == "Legacy Document"
        assert result["document"]["summary"] == "Legacy content"
        assert result["document"]["chunks"][0]["chunk_id"] == "legacy-id"
        mock_store.get_by_ids.assert_called_once_with(["legacy-id"])

    def test_error_response_format(self):
        response = GetDocumentSummaryTool._error_response("Test error")

        assert response["success"] is False
        assert response["error"] == "Test error"


class TestGetDocumentSummaryIntegration:
    def test_tool_with_mocked_chroma_collection_shape(self):
        mock_store = MagicMock()
        mock_store.list_records.side_effect = AttributeError("not supported")
        mock_store._collection.get.return_value = {
            "ids": ["v0", "v1", "v2"],
            "metadatas": [
                _record("v0", chunk_id="chunk-0", source_ref="doc-a", chunk_index=0, text="")["metadata"],
                _record("v1", chunk_id="chunk-1", source_ref="doc-a", chunk_index=1, text="")["metadata"],
                _record("v2", chunk_id="chunk-2", source_ref="doc-a", chunk_index=2, text="")["metadata"],
            ],
            "documents": ["A0", "A1", "A2"],
        }
        tool = GetDocumentSummaryTool(vector_store=mock_store)

        result = tool.execute(chunk_id="chunk-1", context_window=10)

        assert result["success"] is True
        assert result["document"]["title"] == "RAG Architecture Guide"
        assert result["document"]["returned_chunk_count"] == 3

    def test_settings_are_still_loaded(self):
        mock_settings = MagicMock()
        mock_settings.get.return_value = "default"
        mock_store = MagicMock()
        mock_store.get_by_ids.return_value = [
            {
                "id": "doc-a",
                "metadata": {"chunk_id": "doc-a", "source": "a.pdf"},
                "text": "A",
            }
        ]

        with patch("src.mcp_server.tools.get_document_summary.get_settings", return_value=mock_settings):
            tool = GetDocumentSummaryTool(vector_store=mock_store)
            result = tool.execute(doc_id="doc-a")

        assert result["success"] is True
        mock_settings.get.assert_called()
