"""NATOSYMBOL MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from natosymbol.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-natosymbol[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-natosymbol[mcp]'")
        return 1
    app = FastMCP("natosymbol")

    @app.tool()
    def natosymbol_scan(target: str) -> str:
        """Generate and validate APP-6/MIL-STD-2525 symbol identification codes (SIDC).. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
