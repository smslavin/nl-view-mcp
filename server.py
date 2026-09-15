"""nl-view-mcp -- one MCP tool: build_view(instruction).

Startup:
  python server.py

Environment:
  NL_VIEW_MCP_PORT   (default 8010)
  SQLITE_PATH        path to the synthetic telemetry SQLite file (default ./data/telemetry.db)
  ANTHROPIC_API_KEY  used only for the heuristic-fallback classification call

build_view discovers the tag catalog, resolves the instruction into an
Intent via heuristics (intent.py), falls back to Claude only when the
heuristic can't decide (llm_fallback.py), runs the query and emits a widget
spec (widgets.py), and stores it under a ui://view/<slug> resource. The
`ui://` scheme here is a naming convention, not the literal MCP Apps
HTML-in-an-iframe spec -- see README for why.
"""

import json
import os
import sqlite3
import uuid
from typing import Callable

from dotenv import load_dotenv
from mcp.server import MCPServer

from db import discover_mes, discover_schema, init_db
from intent import understand_instruction
from llm_fallback import classify_with_llm
from widgets import build_widget_spec

load_dotenv()

PORT = int(os.environ.get("NL_VIEW_MCP_PORT", 8010))
SQLITE_PATH = os.environ.get("SQLITE_PATH", "./data/telemetry.db")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

mcp = MCPServer("nl-view-mcp")

_VIEW_STORE: dict[str, dict] = {}


def _connect() -> sqlite3.Connection:
    return init_db(SQLITE_PATH)


def run_build_view(
    instruction: str,
    conn: sqlite3.Connection,
    llm_classify: Callable[[str, list[dict]], object] = classify_with_llm,
) -> dict:
    """The actual build_view logic, independent of the MCP tool wrapper so
    it's directly unit-testable against a plain sqlite3.Connection."""
    tags = discover_schema(conn) + discover_mes(conn)
    intent = understand_instruction(instruction, tags)
    if intent.chart_type is None:
        intent = llm_classify(instruction, tags)
    return build_widget_spec(intent, tags, conn)


@mcp.tool()
def build_view(instruction: str) -> str:
    """Given a plain-English instruction, discover available telemetry,
    decide what to query and how to visualize it, and emit a ui://view/<slug>
    JSON widget-spec resource. Returns {"uri": "..."}."""
    conn = _connect()
    try:
        spec = run_build_view(instruction, conn)
    finally:
        conn.close()

    slug = f"{spec['chart_type']}-{uuid.uuid4().hex[:8]}"
    _VIEW_STORE[slug] = spec
    return json.dumps({"uri": f"ui://view/{slug}"})


@mcp.resource("ui://view/{slug}", mime_type="application/json")
def get_view(slug: str) -> str:
    spec = _VIEW_STORE.get(slug)
    if spec is None:
        raise ValueError(f"Unknown view: {slug}")
    return json.dumps(spec)


if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    # mcp.run(transport="streamable-http", ...) has no CORS knob, and the
    # browser-based Vue client needs one -- build the ASGI app ourselves and
    # wrap it. Streamable HTTP (not SSE, which the MCP TS SDK now deprecates)
    # so the client can use StreamableHTTPClientTransport.
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    uvicorn.run(app, host="127.0.0.1", port=PORT)
