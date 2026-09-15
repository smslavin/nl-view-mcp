"""SQLite schema for the synthetic OPC-UA-shaped telemetry store.

Two tables: `tags` (the node/point catalog) and `readings` (time-series
values). This stands in for the InfluxDB layer described in the brief --
same query shape (filter by tag, filter by time range), cheap to stand up
for a throwaway prototype.
"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tags (
    node_id TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    kind    TEXT NOT NULL CHECK (kind IN ('tank_level', 'pump_run_state', 'flow_rate')),
    unit    TEXT NOT NULL,
    zone    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    tag_id TEXT NOT NULL REFERENCES tags(node_id),
    ts     INTEGER NOT NULL,
    value  REAL NOT NULL,
    PRIMARY KEY (tag_id, ts)
);
"""


def init_db(path: str | Path) -> sqlite3.Connection:
    """Create (if needed) and return a connection with the schema applied."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def discover_schema(conn: sqlite3.Connection) -> list[dict]:
    """The tag catalog: node_id/name/kind/unit/zone for every known tag.

    This is the schema-discovery step build_view runs internally before
    deciding what to query -- not exposed as its own MCP tool.
    """
    cursor = conn.execute("SELECT node_id, name, kind, unit, zone FROM tags")
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
