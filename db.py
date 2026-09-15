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
    -- 'flow_rate_aux' is the one auxiliary tag seed_routes() adds for the
    -- divergent-zone demo (see generator.py) -- kept out of the three
    -- telemetry kinds' matching in intent.py deliberately, so it only ever
    -- shows up via the flow widget, never as a stray series on a bar/line/stat.
    kind    TEXT NOT NULL CHECK (kind IN ('tank_level', 'pump_run_state', 'flow_rate', 'flow_rate_aux')),
    unit    TEXT NOT NULL,
    zone    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    tag_id TEXT NOT NULL REFERENCES tags(node_id),
    ts     INTEGER NOT NULL,
    value  REAL NOT NULL,
    PRIMARY KEY (tag_id, ts)
);

CREATE TABLE IF NOT EXISTS lines (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    ideal_rate_per_hour  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS shifts (
    id         TEXT PRIMARY KEY,
    line_id    TEXT NOT NULL REFERENCES lines(id),
    started_at INTEGER NOT NULL,
    ended_at   INTEGER
);

CREATE TABLE IF NOT EXISTS production_events (
    shift_id   TEXT NOT NULL REFERENCES shifts(id),
    ts         INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('good_unit', 'reject_unit', 'downtime_start', 'downtime_end')
    )
);

-- Physical piping between tags within a zone (tank feeds the pump, the pump
-- feeds the flow meter), for the "flow" widget. Every zone but one routes as
-- a straight chain; the divergent zone's pump feeds two flow meters, so the
-- flow widget has a real branch to render, not just a uniform path -- see
-- generator.py's generate_routes.
CREATE TABLE IF NOT EXISTS routes (
    zone     TEXT NOT NULL,
    from_tag TEXT NOT NULL REFERENCES tags(node_id),
    to_tag   TEXT NOT NULL REFERENCES tags(node_id)
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


def discover_mes(conn: sqlite3.Connection) -> list[dict]:
    """One pseudo-tag per production line (kind='oee'), in the same shape
    discover_schema returns -- intent.py and widgets.py work against a flat
    list of {node_id, name, kind, unit, zone} regardless of whether it came
    from the telemetry tag catalog or the production-line catalog. `zone`
    holds the line id, standing in for "the grouping dimension" rather than
    a literal plant zone.
    """
    cursor = conn.execute("SELECT id, name FROM lines")
    columns = [d[0] for d in cursor.description]
    lines = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return [
        {
            "node_id": f"oee.{line['id']}",
            "name": f"{line['name']} OEE",
            "kind": "oee",
            "unit": "%",
            "zone": line["id"],
        }
        for line in lines
    ]
