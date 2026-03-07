"""
Smart Knowledge Hub - Modular RAG System with MCP Server

A production-grade Retrieval-Augmented Generation (RAG) system designed with:
- Full pluggable architecture (LLM/Embedding/VectorStore can be swapped)
- Mixed modal support (PDF + Web scraping)
- Comprehensive observability (tracing + Dashboard)
- MCP Server integration for seamless Copilot/Claude integration

Project Structure:
- mcp_server: MCP Server interface (JSON-RPC 2.0 protocol)
- core: Core business logic (Query Engine, Trace Collection)
- ingestion: Data ingestion pipeline (Load → Split → Transform → Embed → Upsert)
- libs: Pluggable abstraction layer (Factory pattern + Base interfaces)
- observability: Tracing infrastructure & Dashboard
"""

__version__ = "0.1.0"
