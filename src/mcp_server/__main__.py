"""MCP Server module entry point.

Allows running the server with:
    python -m src.mcp_server.server
"""

import asyncio
from src.mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
