"""Unit Tests for Protocol Handler - JSON-RPC 2.0 Protocol.

Tests cover:
- Capability negotiation (initialize)
- Tool schema advertisement (tools/list)
- Tool invocation routing (tools/call)
- Error handling with proper JSON-RPC codes
"""

import pytest
from typing import Any, Dict

from src.mcp_server.protocol_handler import (
    ProtocolHandler,
    ToolSchema,
    JSONRPCError,
    InvalidRequest,
    MethodNotFound,
    InvalidParams,
    InternalError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_tools_registry() -> Dict[str, ToolSchema]:
    """Create sample tools registry for testing."""
    return {
        "query_knowledge_hub": ToolSchema(
            name="query_knowledge_hub",
            description="Search knowledge hub with hybrid retrieval",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "collection": {"type": "string", "default": "default"}
                },
                "required": ["query"]
            }
        ),
        "list_collections": ToolSchema(
            name="list_collections",
            description="List available collections",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        "get_document_summary": ToolSchema(
            name="get_document_summary",
            description="Get summary of a document",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"}
                },
                "required": ["doc_id"]
            }
        )
    }


@pytest.fixture
def sample_executor():
    """Create sample tool executor for testing."""
    def executor(tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Mock executor that returns predictable results."""
        if tool_name == "query_knowledge_hub":
            return {"results": [{"chunk_id": "1", "score": 0.95, "text": "mock result"}]}
        elif tool_name == "list_collections":
            return {"collections": ["default", "test"]}
        elif tool_name == "get_document_summary":
            return {"summary": f"Summary of {arguments.get('doc_id')}"}
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    return executor


@pytest.fixture
def handler(sample_tools_registry, sample_executor) -> ProtocolHandler:
    """Create ProtocolHandler instance for testing."""
    return ProtocolHandler(
        server_name="test-server",
        server_version="1.0.0",
        tools_registry=sample_tools_registry,
        tool_executor=sample_executor
    )


# ============================================================================
# Tests: Initialization & Setup
# ============================================================================

class TestProtocolHandlerInitialization:
    """Test ProtocolHandler initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with minimal parameters."""
        handler = ProtocolHandler()
        assert handler.server_name == "knowledge-hub-rag-server"
        assert handler.server_version == "1.0.0"
        assert handler.tools_registry == {}
        assert handler.tool_executor is None
    
    def test_init_with_custom_values(self, sample_tools_registry, sample_executor):
        """Test initialization with custom values."""
        handler = ProtocolHandler(
            server_name="custom-server",
            server_version="2.0.0",
            tools_registry=sample_tools_registry,
            tool_executor=sample_executor
        )
        assert handler.server_name == "custom-server"
        assert handler.server_version == "2.0.0"
        assert len(handler.tools_registry) == 3
        assert handler.tool_executor is not None
    
    def test_register_tool(self, handler):
        """Test registering a tool after initialization."""
        new_tool = ToolSchema(
            name="new_tool",
            description="A new tool",
            inputSchema={"type": "object"}
        )
        handler.register_tool(new_tool)
        assert "new_tool" in handler.tools_registry
        assert handler.tools_registry["new_tool"].name == "new_tool"
    
    def test_set_tool_executor(self, handler):
        """Test setting tool executor after initialization."""
        def new_executor(name: str, args: Dict) -> Any:
            return {"result": "executed"}
        
        handler.set_tool_executor(new_executor)
        assert handler.tool_executor is not None


# ============================================================================
# Tests: Initialize Request
# ============================================================================

class TestHandleInitialize:
    """Test handle_initialize method."""
    
    def test_initialize_success(self, handler):
        """Test successful initialize request."""
        response = handler.handle_initialize()
        
        assert "serverInfo" in response
        assert response["serverInfo"]["name"] == "test-server"
        assert response["serverInfo"]["version"] == "1.0.0"
        
        assert "capabilities" in response
        assert "tools" in response["capabilities"]
        
        assert "protocolVersion" in response
    
    def test_initialize_with_params(self, handler):
        """Test initialize with client parameters."""
        params = {
            "clientInfo": {"name": "test-client", "version": "1.0"},
            "capabilities": {}
        }
        response = handler.handle_initialize(params)
        
        assert "serverInfo" in response
        assert "capabilities" in response
    
    def test_initialize_tools_capability(self, handler):
        """Test tools capability in initialize response."""
        response = handler.handle_initialize()
        
        tools_cap = response["capabilities"]["tools"]
        assert "listChanged" in tools_cap
        assert tools_cap["listChanged"] is False  # Tools list is static


# ============================================================================
# Tests: Tools/List Request
# ============================================================================

class TestHandleToolsList:
    """Test handle_tools_list method."""
    
    def test_list_empty(self):
        """Test listing when no tools registered."""
        handler = ProtocolHandler()
        response = handler.handle_tools_list()
        
        assert "tools" in response
        assert response["tools"] == []
    
    def test_list_all_tools(self, handler):
        """Test listing all registered tools."""
        response = handler.handle_tools_list()
        
        assert "tools" in response
        tools = response["tools"]
        assert len(tools) == 3
        
        tool_names = {t["name"] for t in tools}
        assert "query_knowledge_hub" in tool_names
        assert "list_collections" in tool_names
        assert "get_document_summary" in tool_names
    
    def test_list_tool_schema_structure(self, handler):
        """Test that tool schemas have required fields."""
        response = handler.handle_tools_list()
        
        for tool in response["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # Validate inputSchema structure
            schema = tool["inputSchema"]
            assert "type" in schema or "properties" in schema
    
    def test_list_specific_tool_fields(self, handler):
        """Test specific tool field values."""
        response = handler.handle_tools_list()
        
        query_tool = next(t for t in response["tools"] if t["name"] == "query_knowledge_hub")
        assert query_tool["description"] == "Search knowledge hub with hybrid retrieval"
        assert "properties" in query_tool["inputSchema"]
        assert "query" in query_tool["inputSchema"]["properties"]


# ============================================================================
# Tests: Tools/Call Request
# ============================================================================

class TestHandleToolsCall:
    """Test handle_tools_call method."""
    
    def test_call_success(self, handler):
        """Test successful tool call."""
        result = handler.handle_tools_call(
            "query_knowledge_hub",
            {"query": "test query", "top_k": 5}
        )
        
        assert "content" in result
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
    
    def test_call_with_empty_arguments(self, handler):
        """Test tool call with no arguments."""
        result = handler.handle_tools_call("list_collections", {})
        
        assert "content" in result
        assert result["content"][0]["type"] == "text"
    
    def test_call_with_none_arguments(self, handler):
        """Test tool call with None arguments."""
        result = handler.handle_tools_call("list_collections", None)
        
        assert "content" in result
    
    def test_call_nonexistent_tool(self, handler):
        """Test calling a tool that doesn't exist."""
        with pytest.raises(MethodNotFound) as exc_info:
            handler.handle_tools_call("nonexistent_tool", {})
        
        assert exc_info.value.code == -32601
        assert "nonexistent_tool" in str(exc_info.value)
    
    def test_call_invalid_arguments_type(self, handler):
        """Test calling with invalid arguments type."""
        with pytest.raises(InvalidParams) as exc_info:
            handler.handle_tools_call("query_knowledge_hub", "not a dict")
        
        assert exc_info.value.code == -32602
    
    def test_call_without_executor(self, sample_tools_registry):
        """Test tool call when no executor is configured."""
        handler = ProtocolHandler(
            tools_registry=sample_tools_registry,
            tool_executor=None
        )
        
        with pytest.raises(InternalError) as exc_info:
            handler.handle_tools_call("query_knowledge_hub", {"query": "test"})
        
        assert exc_info.value.code == -32603


# ============================================================================
# Tests: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and JSON-RPC error codes."""
    
    def test_invalid_request_error(self):
        """Test InvalidRequest error."""
        error = InvalidRequest("Invalid request format")
        assert error.code == -32600
    
    def test_method_not_found_error(self):
        """Test MethodNotFound error."""
        error = MethodNotFound("Unknown method")
        assert error.code == -32601
    
    def test_invalid_params_error(self):
        """Test InvalidParams error."""
        error = InvalidParams("Bad parameters")
        assert error.code == -32602
    
    def test_internal_error_error(self):
        """Test InternalError error."""
        error = InternalError("Server error")
        assert error.code == -32603
    
    def test_error_with_data(self):
        """Test error with additional data field."""
        error = InternalError("Error details", data={"extra": "info"})
        assert error.data == {"extra": "info"}
    
    def test_to_jsonrpc_error_response(self, handler):
        """Test conversion of error to JSON-RPC error response."""
        error = MethodNotFound("Tool not found")
        response = handler.to_jsonrpc_error_response(error, request_id=123)
        
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Tool not found"
        assert response["id"] == 123
    
    def test_error_response_without_request_id(self, handler):
        """Test error response without request ID."""
        error = InvalidRequest("Invalid")
        response = handler.to_jsonrpc_error_response(error)
        
        assert response["jsonrpc"] == "2.0"
        assert "id" not in response
    
    def test_tool_execution_exception_handling(self, sample_tools_registry):
        """Test that tool execution exceptions are caught and converted."""
        def failing_executor(name: str, args: Dict) -> Any:
            raise ValueError("Tool failed")
        
        handler = ProtocolHandler(
            tools_registry=sample_tools_registry,
            tool_executor=failing_executor
        )
        
        with pytest.raises(InternalError) as exc_info:
            handler.handle_tools_call("query_knowledge_hub", {"query": "test"})
        
        # Stack trace should not be exposed
        assert "ValueError" in str(exc_info.value)
        assert exc_info.value.code == -32603


# ============================================================================
# Integration Tests
# ============================================================================

class TestProtocolHandlerIntegration:
    """Integration tests for full workflow."""
    
    def test_full_workflow(self, handler):
        """Test complete workflow: initialize -> list -> call."""
        # Step 1: Initialize
        init_response = handler.handle_initialize()
        assert "serverInfo" in init_response
        assert "capabilities" in init_response
        
        # Step 2: List tools
        list_response = handler.handle_tools_list()
        assert len(list_response["tools"]) == 3
        
        # Step 3: Call tool
        call_response = handler.handle_tools_call(
            "query_knowledge_hub",
            {"query": "test"}
        )
        assert "content" in call_response
    
    def test_error_workflow(self, handler):
        """Test error handling in workflow."""
        # Valid initialize
        init_response = handler.handle_initialize()
        assert "serverInfo" in init_response
        
        # Invalid tool call
        with pytest.raises(MethodNotFound):
            handler.handle_tools_call("invalid", {})
    
    def test_multiple_tool_calls(self, handler):
        """Test multiple consecutive tool calls."""
        results = []
        
        # Call different tools
        results.append(handler.handle_tools_call("list_collections", {}))
        results.append(handler.handle_tools_call("query_knowledge_hub", {"query": "test"}))
        results.append(handler.handle_tools_call("get_document_summary", {"doc_id": "123"}))
        
        # All should succeed
        assert len(results) == 3
        for result in results:
            assert "content" in result
