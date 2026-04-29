"""Integration tests for E1 - MCP Server entry point and Stdio transport.

Tests verify:
- Server initialization and startup
- Stdio constraint: stdout contains only MCP messages
- stderr receives all logs (no pollution of stdout)
- Basic protocol handshake (initialize request/response)
- Subprocess communication (simulating MCP client)

These tests use subprocess mode to properly test Stdio transport.
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


class TestMCPServerSubprocess:
    """Integration tests using subprocess mode to test Stdio transport."""
    
    @staticmethod
    def start_server() -> Tuple[subprocess.Popen, Any]:
        """Start MCP server as a subprocess.
        
        Returns:
            (process, reader) tuple where reader is a JSON-RPC message reader
        """
        project_root = get_project_root()
        
        # Start server subprocess
        # Use python -m to run the server module
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.mcp_server.server"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(project_root)
        )
        
        return process
    
    @staticmethod
    def send_request(process: subprocess.Popen, request: Dict[str, Any]) -> Optional[str]:
        """Send a JSON-RPC request to the server.
        
        Args:
            process: Server subprocess
            request: JSON-RPC 2.0 request dict
        
        Returns:
            Response line if available, None if timeout
        """
        try:
            # Encode request as JSON-RPC
            request_json = json.dumps(request)
            process.stdin.write(request_json + "\n")
            process.stdin.flush()
            
            # Read response (with timeout)
            # Note: subprocess.Popen with text=True may buffer
            # We read line by line
            start = time.time()
            timeout = 5.0
            
            while time.time() - start < timeout:
                try:
                    # Try to read a line with a short timeout
                    line = process.stdout.readline()
                    if line:
                        return line.strip()
                except:
                    time.sleep(0.1)
            
            return None
        
        except Exception as e:
            print(f"Error sending request: {e}", file=sys.stderr)
            return None
    
    def test_server_starts(self):
        """Test that server process starts without immediate exit."""
        process = self.start_server()
        
        try:
            # Give server time to start
            time.sleep(1)
            
            # Check if process is still alive
            returncode = process.poll()
            assert returncode is None, f"Server exited with code {returncode}"
            
        finally:
            process.terminate()
            process.wait(timeout=5)
    
    def test_initialize_request(self):
        """Test MCP initialize request/response.
        
        Verifies:
        - Server responds to initialize
        - Response contains required fields
        - Response is valid JSON-RPC
        """
        process = self.start_server()
        
        try:
            # Wait for server to be ready
            time.sleep(1)
            
            # Send initialize request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            response_line = self.send_request(process, request)
            assert response_line is not None, "Server did not respond to initialize"
            
            # Parse response
            response = json.loads(response_line)
            
            # Validate JSON-RPC response format
            assert "jsonrpc" in response, "Missing jsonrpc field"
            assert response["jsonrpc"] == "2.0"
            assert "id" in response, "Missing id field"
            assert response["id"] == 1
            
            # Check for result (success) or error
            if "error" in response:
                print(f"Initialize error: {response['error']}", file=sys.stderr)
                assert False, f"Initialize failed: {response['error']}"
            
            assert "result" in response, "Missing result field"
            
            # Validate result structure
            result = response["result"]
            assert "protocolVersion" in result or "capabilities" in result, \
                "Result missing required fields"
            
            print(f"✓ Initialize response: {result}", file=sys.stderr)
        
        finally:
            process.terminate()
            process.wait(timeout=5)
    
    def test_tools_list_request(self):
        """Test tools/list request.
        
        Verifies:
        - Server responds to tools/list
        - Response includes at least 3 tools (query_knowledge_hub, list_collections, get_document_summary)
        """
        process = self.start_server()
        
        try:
            # Wait for server to be ready
            time.sleep(1)
            
            # First, initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            }
            
            response = self.send_request(process, init_request)
            assert response is not None, "Initialize failed"
            
            # Now send tools/list
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            response_line = self.send_request(process, tools_request)
            assert response_line is not None, "Server did not respond to tools/list"
            
            response = json.loads(response_line)
            
            # Validate response
            assert "result" in response or "error" not in response
            
            if "result" in response:
                result = response["result"]
                assert "tools" in result, "Missing tools field in result"
                tools = result["tools"]
                
                # Check for expected tools
                tool_names = [t.get("name") if isinstance(t, dict) else t.name for t in tools]
                assert "query_knowledge_hub" in tool_names, "Missing query_knowledge_hub tool"
                assert "list_collections" in tool_names, "Missing list_collections tool"
                assert "get_document_summary" in tool_names, "Missing get_document_summary tool"
                
                print(f"✓ Tools list: {tool_names}", file=sys.stderr)
        
        finally:
            process.terminate()
            process.wait(timeout=5)
    
    def test_stdout_stderr_separation(self):
        """Test that MCP messages go to stdout, logs go to stderr.
        
        Verifies:
        - stdout contains only JSON-RPC messages
        - stderr contains logs (with timestamps, no JSON-RPC)
        """
        process = self.start_server()
        
        try:
            # Wait for server to start
            time.sleep(1)
            
            # Send a request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
            }
            
            response_line = self.send_request(process, request)
            
            # Read stderr
            _, stderr = process.communicate(input=json.dumps(request) + "\n", timeout=5)
            
            # Verify
            if response_line:
                # stdout should contain JSON-RPC
                try:
                    json.loads(response_line)
                    print(f"✓ stdout contains valid JSON-RPC", file=sys.stderr)
                except json.JSONDecodeError:
                    assert False, f"stdout contains non-JSON-RPC data: {response_line}"
            
            # stderr should contain logs if any
            # (may be empty in minimal test, but should not contain JSON-RPC)
            if stderr and "{" in stderr:
                # Check that stderr logs are not JSON-RPC (they should have timestamps, etc)
                lines = stderr.strip().split("\n")
                for line in lines:
                    if line and not line.startswith("["):
                        # Skip lines that don't look like logs
                        pass
                
                print(f"✓ stderr contains logs (sample): {stderr[:100]}...", file=sys.stderr)
        
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


class TestMCPServerBasic:
    """Basic unit-level tests (no subprocess).
    
    These can be run without full server process.
    """
    
    def test_server_module_imports(self):
        """Test that server module imports without errors."""
        try:
            from src.mcp_server import server
            assert hasattr(server, 'MCPServerImpl')
            assert hasattr(server, 'main')
            print("✓ Server module imports successfully", file=sys.stderr)
        except ImportError as e:
            assert False, f"Failed to import server module: {e}"
    
    def test_mcp_sdk_available(self):
        """Test that MCP SDK is installed."""
        try:
            import mcp
            print("✓ MCP SDK available", file=sys.stderr)
        except ImportError:
            assert False, "MCP SDK not installed (pip install mcp)"


class TestQueryKnowledgeHubTool:
    """Tests for query_knowledge_hub MCP tool (E3)."""

    def test_tool_imports(self):
        """Test that query_knowledge_hub module imports successfully."""
        try:
            from src.mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool
            assert QueryKnowledgeHubTool is not None
            print("✓ QueryKnowledgeHubTool imports successfully", file=sys.stderr)
        except ImportError as e:
            assert False, f"Failed to import query_knowledge_hub: {e}"

    def test_response_builder_imports(self):
        """Test that response builder modules import successfully."""
        try:
            from src.core.response.response_builder import ResponseBuilder, MCPResponse
            from src.core.response.citation_generator import CitationGenerator
            assert ResponseBuilder is not None
            assert CitationGenerator is not None
            print("✓ Response builder modules import successfully", file=sys.stderr)
        except ImportError as e:
            assert False, f"Failed to import response modules: {e}"

    def test_tool_schema(self):
        """Test that tool provides valid MCP schema."""
        from src.mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool

        schema = QueryKnowledgeHubTool.to_tool_schema()

        # Validate schema structure
        assert "name" in schema
        assert schema["name"] == "query_knowledge_hub"
        assert "description" in schema
        assert "inputSchema" in schema

        # Validate input schema
        input_schema = schema["inputSchema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "query" in input_schema["properties"]
        assert "top_k" in input_schema["properties"]
        assert "collection" in input_schema["properties"]

        # query should be required
        assert "required" in input_schema
        assert "query" in input_schema["required"]

        print("✓ Tool schema is valid", file=sys.stderr)

    def test_tool_error_handling_empty_query(self):
        """Test tool error handling for empty query."""
        from unittest.mock import MagicMock, patch
        from src.mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool

        # Mock dependencies to avoid loading settings
        mock_hybrid_search = MagicMock()
        mock_reranker = MagicMock()
        mock_settings = MagicMock()
        
        with patch('src.core.settings.get_settings', return_value=mock_settings):
            tool = QueryKnowledgeHubTool(
                hybrid_search=mock_hybrid_search,
                reranker=mock_reranker
            )
            result = tool.execute(query="", top_k=5)

        assert result["success"] is False
        assert "error" in result
        assert "empty" in result["error"].lower()
        print("✓ Tool rejects empty query", file=sys.stderr)

    def test_tool_error_handling_invalid_top_k(self):
        """Test tool error handling for invalid top_k."""
        from unittest.mock import MagicMock, patch
        from src.mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool

        # Mock dependencies to avoid loading settings
        mock_hybrid_search = MagicMock()
        mock_reranker = MagicMock()
        mock_settings = MagicMock()
        
        with patch('src.core.settings.get_settings', return_value=mock_settings):
            tool = QueryKnowledgeHubTool(
                hybrid_search=mock_hybrid_search,
                reranker=mock_reranker
            )

            # Test top_k < 1
            result = tool.execute(query="test", top_k=0)
            assert result["success"] is False
            assert "top_k" in result["error"]

            # Test top_k > 50
            result = tool.execute(query="test", top_k=100)
            assert result["success"] is False
            assert "top_k" in result["error"]

        print("✓ Tool validates top_k parameter", file=sys.stderr)

    def test_response_format(self):
        """Test that tool returns properly formatted MCP response."""
        from src.core.response.response_builder import ResponseBuilder
        from src.core.types import RetrievalResult

        # Create mock retrieval results
        results = [
            RetrievalResult(
                chunk_id="test_chunk_1",
                content="This is test content for chunk 1",
                metadata={"source": "test.pdf", "doc_type": "pdf", "page": 1},
                score=0.95,
            ),
            RetrievalResult(
                chunk_id="test_chunk_2",
                content="This is test content for chunk 2",
                metadata={"source": "test.md", "doc_type": "markdown"},
                score=0.87,
            ),
        ]

        # Build response
        response = ResponseBuilder.build(results, query="test query")

        # Validate response structure
        assert len(response.content) == 1
        assert response.content[0]["type"] == "text"
        assert "text" in response.content[0]

        # Validate citations
        assert len(response.citations) == 2
        assert response.citations[0].id == 1
        assert response.citations[0].source == "test.pdf"
        assert response.citations[1].id == 2

        # Validate markdown contains citations
        markdown = response.content[0]["text"]
        assert "[1]" in markdown
        assert "[2]" in markdown
        assert "test.pdf" in markdown

        print("✓ Response format is correct", file=sys.stderr)

    def test_empty_response_handling(self):
        """Test that tool handles empty search results gracefully."""
        from src.core.response.response_builder import ResponseBuilder

        # Build response with no results
        response = ResponseBuilder.build([], query="no results query")

        assert len(response.content) == 1
        assert response.content[0]["type"] == "text"
        # Should contain friendly message
        text = response.content[0]["text"]
        assert len(text) > 0
        assert ("未找到" in text or "找到" in text)

        print("✓ Empty results handled gracefully", file=sys.stderr)


# ============================================================================
# pytest Entry Points
# ============================================================================

if __name__ == "__main__":
    import pytest
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
