"""Protocol Handler - JSON-RPC 2.0 Protocol Implementation.

This module implements the JSON-RPC 2.0 protocol layer for MCP, handling:
- Method routing (initialize, tools/list, tools/call)
- Capability negotiation
- Error handling with proper JSON-RPC error codes
- Tool schema introspection

JSON-RPC 2.0 Error Codes:
- -32700: Parse error
- -32600: Invalid Request
- -32601: Method not found
- -32602: Invalid params
- -32603: Internal error
- -32000 to -32099: Server error (reserved)

Reference: https://www.jsonrpc.org/specification
"""

import logging
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass


logger = logging.getLogger("mcp_server")


# ============================================================================
# JSON-RPC 2.0 Error Definitions
# ============================================================================

class JSONRPCError(Exception):
    """Base exception for JSON-RPC errors."""
    
    def __init__(self, code: int, message: str, data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class InvalidRequest(JSONRPCError):
    """Error code -32600: Invalid Request."""
    def __init__(self, message: str, data: Optional[Dict] = None):
        super().__init__(-32600, message, data)


class MethodNotFound(JSONRPCError):
    """Error code -32601: Method not found."""
    def __init__(self, message: str, data: Optional[Dict] = None):
        super().__init__(-32601, message, data)


class InvalidParams(JSONRPCError):
    """Error code -32602: Invalid params."""
    def __init__(self, message: str, data: Optional[Dict] = None):
        super().__init__(-32602, message, data)


class InternalError(JSONRPCError):
    """Error code -32603: Internal error."""
    def __init__(self, message: str, data: Optional[Dict] = None):
        super().__init__(-32603, message, data)


# ============================================================================
# Protocol Handler
# ============================================================================

@dataclass
class ToolSchema:
    """Tool schema for capability advertisement."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ProtocolHandler:
    """JSON-RPC 2.0 Protocol Handler for MCP.
    
    Manages:
    - Capability negotiation (initialize)
    - Tool schema advertisement (tools/list)
    - Tool invocation routing (tools/call)
    - Error handling with proper JSON-RPC codes
    """
    
    def __init__(self, 
                 server_name: str = "knowledge-hub-rag-server",
                 server_version: str = "1.0.0",
                 tools_registry: Optional[Dict[str, ToolSchema]] = None,
                 tool_executor: Optional[Callable[[str, Dict], Any]] = None):
        """Initialize Protocol Handler.
        
        Args:
            server_name: Human-readable server name
            server_version: Server version string
            tools_registry: Dict of tool_name -> ToolSchema
            tool_executor: Callable(tool_name, arguments) -> result
                          Used to route tool/call requests to actual implementations
        """
        self.server_name = server_name
        self.server_version = server_version
        self.tools_registry = tools_registry or {}
        self.tool_executor = tool_executor
        
        logger.info(f"ProtocolHandler initialized: {server_name} v{server_version} "
                   f"with {len(self.tools_registry)} tools")
    
    def handle_initialize(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle initialize request - capability negotiation.
        
        Args:
            params: Client parameters (usually contains client_info, capabilities)
            
        Returns:
            Server response with serverInfo and capabilities
            
        Raises:
            InvalidRequest: If params format is invalid
        """
        try:
            logger.debug(f"Initialize request received with params: {params}")
            
            # Build capabilities response
            capabilities = {
                "tools": {
                    "listChanged": False  # Tools list is static, won't change during session
                }
            }
            
            response = {
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.server_version
                },
                "capabilities": capabilities,
                "protocolVersion": "2024-11-05"  # MCP protocol version
            }
            
            logger.debug(f"Initialize response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error in handle_initialize: {e}", exc_info=True)
            raise InternalError(str(e))
    
    def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request - return registered tool schemas.
        
        Returns:
            List of tool schemas with name, description, inputSchema
            
        Raises:
            InternalError: If schema building fails
        """
        try:
            logger.debug(f"tools/list request received")
            
            tools_list = []
            for tool_name, schema in self.tools_registry.items():
                tool_dict = {
                    "name": schema.name,
                    "description": schema.description,
                    "inputSchema": schema.inputSchema
                }
                tools_list.append(tool_dict)
            
            response = {
                "tools": tools_list
            }
            
            logger.debug(f"tools/list response: {len(tools_list)} tools")
            return response
            
        except Exception as e:
            logger.error(f"Error in handle_tools_list: {e}", exc_info=True)
            raise InternalError(str(e))
    
    def handle_tools_call(self, 
                         name: str, 
                         arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle tools/call request - route to tool implementation.
        
        Args:
            name: Tool name to invoke
            arguments: Tool arguments dict
            
        Returns:
            Tool result
            
        Raises:
            MethodNotFound: If tool doesn't exist
            InvalidParams: If arguments are invalid
            InternalError: If tool execution fails
        """
        try:
            logger.debug(f"tools/call request: {name} with args: {arguments}")
            
            # Check if tool exists
            if name not in self.tools_registry:
                logger.warning(f"Tool not found: {name}")
                raise MethodNotFound(f"Tool '{name}' not found")
            
            # Validate arguments (basic check)
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                logger.warning(f"Invalid arguments type for {name}: {type(arguments)}")
                raise InvalidParams(f"Arguments must be a dict, got {type(arguments).__name__}")
            
            # Route to executor if available
            if self.tool_executor is None:
                logger.warning("No tool executor configured")
                raise InternalError("Tool executor not available")
            
            logger.debug(f"Executing tool: {name} with arguments: {arguments}")
            result = self.tool_executor(name, arguments)
            
            logger.debug(f"Tool execution result: {name} -> {result}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
            
        except JSONRPCError:
            # Re-raise JSON-RPC errors as-is
            raise
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            # Don't leak stack trace in error message
            raise InternalError(f"Tool execution failed: {type(e).__name__}")
    
    def register_tool(self, schema: ToolSchema) -> None:
        """Register a tool schema.
        
        Args:
            schema: ToolSchema object
        """
        self.tools_registry[schema.name] = schema
        logger.debug(f"Tool registered: {schema.name}")
    
    def set_tool_executor(self, executor: Callable[[str, Dict], Any]) -> None:
        """Set the tool executor callback.
        
        Args:
            executor: Callable(tool_name, arguments) -> result
        """
        self.tool_executor = executor
        logger.debug("Tool executor set")
    
    def to_jsonrpc_error_response(self, error: JSONRPCError, 
                                 request_id: Optional[Any] = None) -> Dict[str, Any]:
        """Convert JSONRPCError to JSON-RPC 2.0 error response.
        
        Args:
            error: JSONRPCError exception
            request_id: Request ID from the original request (can be None)
            
        Returns:
            JSON-RPC 2.0 error response dict
        """
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": error.code,
                "message": error.message
            }
        }
        
        if error.data is not None:
            response["error"]["data"] = error.data
        
        if request_id is not None:
            response["id"] = request_id
        
        return response
