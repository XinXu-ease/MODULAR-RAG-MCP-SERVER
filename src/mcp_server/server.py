"""MCP Server Entry Point - Stdio Transport Implementation.

This module implements the Model Context Protocol (MCP) Server following the specification:
- Stdio Transport: stdin for incoming requests, stdout for responses
- JSON-RPC 2.0: Standard message protocol via FastMCP
- Tool Registration: query_knowledge_hub, list_collections, get_document_summary
- Error Handling: Proper JSON-RPC error responses with logging to stderr

Design Principles:
- stdout is exclusively for MCP messages (JSON-RPC)
- All diagnostics/logs go to stderr to avoid protocol pollution
- Graceful error handling with proper exception messages
- Uses FastMCP from mcp.server.fastmcp for simplified Stdio transport

Reference: https://spec.modelcontextprotocol.io/
"""

import sys
import logging
from typing import Any, Dict

# Ensure MCP SDK is available
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print(f"Error: MCP SDK not installed. Please install 'mcp' package: pip install mcp", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Logging Configuration
# ============================================================================

def _setup_logging() -> logging.Logger:
    """Configure logging to output to stderr only (never stdout).
    
    This ensures MCP protocol messages remain uncontaminated on stdout.
    All diagnostic output goes to stderr for Client visibility.
    """
    # Remove any existing handlers
    logging.root.handlers = []
    
    # Create stderr handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt='[%(asctime)s] %(name)s:%(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    
    logger = logging.getLogger("mcp_server")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    return logger


logger = _setup_logging()


# ============================================================================
# MCP Server Implementation using FastMCP
# ============================================================================

class MCPServerImpl:
    """Model Context Protocol Server Implementation using FastMCP.
    
    FastMCP simplifies Stdio transport by:
    - Automatically handling JSON-RPC 2.0 protocol
    - Providing decorators for tool/resource/prompt registration
    - Managing server lifecycle and transport
    
    Handles:
    - Tool registration (query_knowledge_hub, list_collections, get_document_summary)
    - Tool invocation routing
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize MCP Server with FastMCP."""
        self.app = FastMCP("knowledge-hub-rag-server")
        self._register_tools()
        logger.info("MCPServerImpl initialized with FastMCP")
    
    def _register_tools(self) -> None:
        """Register tools using FastMCP decorators."""
        
        @self.app.tool()
        def query_knowledge_hub(
            query: str,
            top_k: int = 5,
            collection: str = "default"
        ) -> Dict[str, Any]:
            """Search knowledge hub with hybrid retrieval (dense + sparse + rerank).
            
            Returns relevant chunks with citations.
            
            Args:
                query: Search query string
                top_k: Number of top results to return (default: 5)
                collection: Filter results to specific collection (default: all)
            
            Returns:
                Dictionary with results list and metadata
            """
            logger.info(f"Query handler: query={query}, top_k={top_k}, collection={collection}")
            
            # Stub response for E1 - TODO (E3): Integrate with HybridSearch + Reranker
            return {
                "results": [
                    {
                        "content": "[STUB] No retrieval results available yet. Implement E3 to enable retrieval.",
                        "metadata": {
                            "doc_id": "stub-001",
                            "source": "stub",
                            "chunk_index": 0
                        },
                        "score": 0.0
                    }
                ],
                "query": query,
                "collection": collection,
                "top_k": top_k
            }
        
        @self.app.tool()
        def list_collections() -> Dict[str, Any]:
            """List all available document collections in the knowledge hub.
            
            Returns:
                Dictionary with collections list
            """
            logger.info("List collections handler")
            
            # Stub response for E1 - TODO (E4): Query DocumentManager for actual collections
            return {
                "collections": [
                    {
                        "name": "default",
                        "description": "Default collection (stub)"
                    }
                ]
            }
        
        @self.app.tool()
        def get_document_summary(
            doc_id: str = "",
            source_ref: str = "",
            chunk_id: str = "",
            collection: str = "",
            context_window: int = 10,
        ) -> Dict[str, Any]:
            """Get summary of a document from a source_ref or chunk_id.
            
            Args:
                doc_id: Backward-compatible lookup ID
                source_ref: Original loaded document reference from a citation
                chunk_id: Exact retrieved chunk ID from a citation
                collection: Optional collection namespace filter
                context_window: Number of neighboring chunks to return on each side
            
            Returns:
                Dictionary with document summary and metadata
            """
            logger.info(
                "Get document summary handler: doc_id=%s, source_ref=%s, chunk_id=%s, collection=%s",
                doc_id,
                source_ref,
                chunk_id,
                collection,
            )
            
            from src.mcp_server.tools.get_document_summary import GetDocumentSummaryTool

            return GetDocumentSummaryTool().execute(
                doc_id=doc_id or None,
                source_ref=source_ref or None,
                chunk_id=chunk_id or None,
                collection=collection or None,
                context_window=context_window,
            )
        
        logger.info("Tools registered: query_knowledge_hub, list_collections, get_document_summary")
    
    async def run_stdio(self) -> None:
        """Start the MCP server using Stdio transport.
        
        This method blocks until the server is shut down.
        Uses FastMCP's built-in Stdio transport handler.
        """
        logger.info("Starting MCP Server with Stdio transport...")
        try:
            # FastMCP.run() handles Stdio transport automatically
            await self.app.run(
                transport="stdio",
                debug=False  # Set to True for verbose debugging
            )
            logger.info("MCP Server shut down cleanly")
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            sys.exit(1)


# ============================================================================
# Entry Point
# ============================================================================

async def main() -> None:
    """Main entry point for the MCP Server."""
    try:
        server = MCPServerImpl()
        await server.run_stdio()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
