"""MCP Server entry point.

Run with: python -m openpulse.mcp_server
Or configure in Hermes/OpenClaw MCP settings.
"""

from openpulse.api.mcp.server import run_mcp_server

if __name__ == "__main__":
    run_mcp_server()
