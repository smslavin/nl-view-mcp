"""Query execution + widget spec emission.

Takes a resolved Intent and turns it into the small declarative JSON shape
served from a ui://view/<slug> resource: widget_type, title, chart_type,
series, size_hint. No markup, no code -- just data.
"""

import sqlite3
import time

from intent import Intent

# The generator seeds readings on a fixed cadence, but the data layer has no
# sampling-rate metadata of its own -- a known simplification for this
# prototype. Real telemetry (or a richer schema) would carry this per-tag.
SAMPLE_INTERVAL_S = 60


def _tags_for(tags: list[dict], kind: str, zones: list[str] | None) -> list[dict]:
    matched = [tag for tag in tags if tag["kind"] == kind]
    if zones:
        matched = [tag for tag in matched if tag["zone"] in zones]
    return matched


def _format_window(window_s: int) -> str:
    if window_s % 3600 == 0:
        hours = window_s // 3600
        return f"Last {hours} Hour" + ("s" if hours != 1 else "")
    minutes = window_s // 60
    return f"Last {minutes} Minutes"


def build_line_spec(intent: Intent, tags: list[dict], conn: sqlite3.Connection) -> dict:
    matched = _tags_for(tags, intent.kind, intent.zones)
    end_ts = int(time.time())
    start_ts = end_ts - intent.window_s

    series = []
    for tag in matched:
        rows = conn.execute(
            "SELECT ts, value FROM readings WHERE tag_id = ? AND ts BETWEEN ? AND ? ORDER BY ts",
            (tag["node_id"], start_ts, end_ts),
        ).fetchall()
        series.append(
            {
                "name": tag["name"],
                "unit": tag["unit"],
                "points": [{"x": ts, "y": value} for ts, value in rows],
            }
        )

    label = intent.kind.replace("_", " ").title()
    return {
        "widget_type": "chart",
        "title": f"{label} — {_format_window(intent.window_s)}",
        "chart_type": "line",
        "series": series,
        "size_hint": {"w": 6, "h": 4},
    }


def _current_shift(conn: sqlite3.Connection, line_id: str) -> tuple[str, int] | None:
    row = conn.execute(
        "SELECT id, started_at FROM shifts WHERE line_id = ? AND ended_at IS NULL "
        "ORDER BY started_at DESC LIMIT 1",
        (line_id,),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _downtime_seconds(conn: sqlite3.Connection, shift_id: str, now_ts: int) -> int:
    """Pairs up downtime_start/downtime_end events; an unmatched trailing
    downtime_start counts as still-down through now_ts."""
    rows = conn.execute(
        "SELECT event_type, ts FROM production_events WHERE shift_id = ? "
        "AND event_type IN ('downtime_start', 'downtime_end') ORDER BY ts",
        (shift_id,),
    ).fetchall()

    total = 0
    open_start = None
    for event_type, ts in rows:
        if event_type == "downtime_start":
            open_start = ts
        elif open_start is not None:  # downtime_end
            total += ts - open_start
            open_start = None
    if open_start is not None:
        total += now_ts - open_start
    return total


def _compute_oee_pct(conn: sqlite3.Connection, line_id: str) -> float:
    """Availability x performance x quality for a line's current (open)
    shift, as a 0-100 percentage. 0.0 if the line has no open shift."""
    shift = _current_shift(conn, line_id)
    if shift is None:
        return 0.0
    shift_id, started_at = shift

    now_ts = int(time.time())
    planned_s = now_ts - started_at
    if planned_s <= 0:
        return 0.0

    run_s = max(planned_s - _downtime_seconds(conn, shift_id, now_ts), 0)

    good, reject = conn.execute(
        "SELECT "
        "  SUM(event_type = 'good_unit'), "
        "  SUM(event_type = 'reject_unit') "
        "FROM production_events WHERE shift_id = ?",
        (shift_id,),
    ).fetchone()
    good, reject, total = good or 0, reject or 0, (good or 0) + (reject or 0)

    ideal_rate = conn.execute(
        "SELECT ideal_rate_per_hour FROM lines WHERE id = ?", (line_id,)
    ).fetchone()[0]

    availability = run_s / planned_s
    actual_rate = total / (run_s / 3600) if run_s > 0 else 0.0
    performance = min(actual_rate / ideal_rate, 1.0) if ideal_rate else 0.0
    quality = good / total if total > 0 else 0.0

    return round(availability * performance * quality * 100, 1)


def _aggregate_for_bar(conn: sqlite3.Connection, tag: dict) -> float:
    if tag["kind"] == "pump_run_state":
        on_count = conn.execute(
            "SELECT COUNT(*) FROM readings WHERE tag_id = ? AND value = 1",
            (tag["node_id"],),
        ).fetchone()[0]
        return round(on_count * SAMPLE_INTERVAL_S / 3600, 2)
    if tag["kind"] == "oee":
        return _compute_oee_pct(conn, tag["zone"])
    avg = conn.execute(
        "SELECT AVG(value) FROM readings WHERE tag_id = ?", (tag["node_id"],)
    ).fetchone()[0]
    return round(avg or 0.0, 2)


# kind -> (unit, series label, "by <this word>"). Kinds not listed here fall
# back to a generic title-cased label grouped "by Zone".
_BAR_LABELS = {
    "pump_run_state": ("hours", "Pump Run Hours", "Zone"),
    "oee": ("%", "OEE", "Line"),
}


def build_bar_spec(intent: Intent, tags: list[dict], conn: sqlite3.Connection) -> dict:
    matched = _tags_for(tags, intent.kind, None)
    by_zone = {tag["zone"]: tag for tag in matched}

    points = []
    for zone in sorted(by_zone):
        tag = by_zone[zone]
        points.append({"x": zone, "y": _aggregate_for_bar(conn, tag)})

    unit, label, group_noun = _BAR_LABELS.get(
        intent.kind,
        (
            next(iter(by_zone.values()))["unit"],
            intent.kind.replace("_", " ").title(),
            "Zone",
        ),
    )

    return {
        "widget_type": "chart",
        "title": f"{label} by {group_noun}",
        "chart_type": "bar",
        "series": [{"name": label, "unit": unit, "points": points}],
        "size_hint": {"w": 6, "h": 4},
    }


def build_stat_spec(intent: Intent, tags: list[dict], conn: sqlite3.Connection) -> dict:
    matched = _tags_for(tags, intent.kind, intent.zones)

    values = []
    for tag in matched:
        row = conn.execute(
            "SELECT value FROM readings WHERE tag_id = ? ORDER BY ts DESC LIMIT 1",
            (tag["node_id"],),
        ).fetchone()
        if row:
            values.append(row[0])

    value = round(sum(values) / len(values), 2) if values else None
    unit = matched[0]["unit"] if matched else ""
    label = intent.kind.replace("_", " ").title()
    return {
        "widget_type": "stat",
        "title": f"Current {label}",
        "chart_type": "stat",
        "series": [{"name": label, "unit": unit, "points": [{"x": "now", "y": value}]}],
        "size_hint": {"w": 3, "h": 2},
    }


def _fmt_ts(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts))


def build_table_spec(intent: Intent, tags: list[dict], conn: sqlite3.Connection) -> dict:
    """Rows-and-columns, for data that's naturally tabular rather than a
    plottable series -- shift records here, but the shape (columns declare a
    `kind` per field, rows are plain dicts keyed by column) is generic. A
    `kind: "code"` column is the renderer's cue to use monospace + truncate +
    full-value-on-hover, same as a lot code gets in mes-mcp's recall UI.
    """
    rows = conn.execute(
        "SELECT s.id, l.name, s.started_at, s.ended_at "
        "FROM shifts s JOIN lines l ON l.id = s.line_id ORDER BY l.name"
    ).fetchall()

    columns = [
        {"key": "line", "label": "Line", "kind": "text"},
        {"key": "started", "label": "Started", "kind": "text"},
        {"key": "ended", "label": "Ended", "kind": "text"},
        {"key": "id", "label": "Shift ID", "kind": "code"},
    ]
    out_rows = [
        {
            "line": line_name,
            "started": _fmt_ts(started_at),
            "ended": _fmt_ts(ended_at) if ended_at is not None else "in progress",
            "id": shift_id,
        }
        for shift_id, line_name, started_at, ended_at in rows
    ]

    return {
        "widget_type": "table",
        "title": "Shift History",
        "chart_type": "table",
        "columns": columns,
        "rows": out_rows,
        "size_hint": {"w": 8, "h": 4},
    }


def build_flow_spec(intent: Intent, tags: list[dict], conn: sqlite3.Connection) -> dict:
    """Node/edge topology for a zone's physical routing -- the one shape line/
    bar/stat can't represent. Scoped to the requested zones, or every zone
    with routing data when none is named. Node labels come from the tag
    catalog already in `tags`; `routes` (zone, from_tag, to_tag) is queried
    directly since it isn't part of tag discovery.
    """
    zones = intent.zones or sorted({
        t["zone"] for t in tags
        if t["kind"] in ("tank_level", "pump_run_state", "flow_rate", "flow_rate_aux")
    })
    by_id = {t["node_id"]: t for t in tags}

    placeholders = ",".join("?" * len(zones))
    route_rows = (
        conn.execute(
            f"SELECT zone, from_tag, to_tag FROM routes WHERE zone IN ({placeholders})", zones,
        ).fetchall()
        if zones else []
    )

    node_ids: dict[str, dict] = {}
    edges = []
    for _zone, from_tag, to_tag in route_rows:
        for node_id in (from_tag, to_tag):
            if node_id not in node_ids:
                tag = by_id.get(node_id)
                node_ids[node_id] = {"id": node_id, "label": tag["name"] if tag else node_id}
        edges.append({"from": from_tag, "to": to_tag})

    title = (
        f"Flow Topology — {', '.join(z.title() for z in zones)}" if intent.zones else "Flow Topology"
    )
    return {
        "widget_type": "flow",
        "title": title,
        "chart_type": "flow",
        "nodes": list(node_ids.values()),
        "edges": edges,
        "size_hint": {"w": 6, "h": 4},
    }


_BUILDERS = {
    "line": build_line_spec, "bar": build_bar_spec, "stat": build_stat_spec,
    "table": build_table_spec, "flow": build_flow_spec,
}


def build_widget_spec(
    intent: Intent, tags: list[dict], conn: sqlite3.Connection
) -> dict:
    return _BUILDERS[intent.chart_type](intent, tags, conn)
