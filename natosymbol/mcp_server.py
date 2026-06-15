"""NATOSYMBOL MCP server — exposes validate/describe as MCP tools."""
from __future__ import annotations

import json
import sys

from natosymbol.core import SIDCError, describe_sidc, validate_sidc


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-natosymbol[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import]
    except Exception:
        print(
            "Install the MCP extra: pip install 'cognis-natosymbol[mcp]'",
            file=sys.stderr,
        )
        return 1
    app = FastMCP("natosymbol")

    @app.tool()
    def natosymbol_validate(sidc: str) -> str:
        """Validate an APP-6/MIL-STD-2525 SIDC string. Returns JSON."""
        try:
            validate_sidc(sidc)
            return json.dumps({"code": sidc, "valid": True})
        except SIDCError as exc:
            return json.dumps({"code": sidc, "valid": False, "error": str(exc)})

    @app.tool()
    def natosymbol_describe(sidc: str) -> str:
        """Decode an APP-6/MIL-STD-2525 SIDC into human-readable fields. Returns JSON."""
        try:
            return json.dumps(describe_sidc(sidc))
        except SIDCError as exc:
            return json.dumps({"error": str(exc)})

    app.run()
    return 0
