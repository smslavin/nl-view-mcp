"""Synthetic telemetry generator.

Produces a small OPC-UA-shaped tag catalog (tank level / pump run state /
flow rate, a few zones) and a rolling window of plausible, noisy readings.
The generation logic (generate_tags / generate_readings) is pure -- no I/O --
so it can be unit tested on its own; seed() is the thin orchestrator that
writes the result into SQLite.
"""

import math
import os
import random
from pathlib import Path

from dotenv import load_dotenv

from db import init_db

ZONES = ["north", "south", "east", "west"]


def generate_tags(zones: list[str] = ZONES) -> list[dict]:
    """One tank_level, pump_run_state, and flow_rate tag per zone."""
    tags = []
    for zone in zones:
        tags.append(
            {
                "node_id": f"{zone}.tank_level",
                "name": f"{zone.title()} Tank Level",
                "kind": "tank_level",
                "unit": "%",
                "zone": zone,
            }
        )
        tags.append(
            {
                "node_id": f"{zone}.pump_run_state",
                "name": f"{zone.title()} Pump Run State",
                "kind": "pump_run_state",
                "unit": "bool",
                "zone": zone,
            }
        )
        tags.append(
            {
                "node_id": f"{zone}.flow_rate",
                "name": f"{zone.title()} Flow Rate",
                "kind": "flow_rate",
                "unit": "gpm",
                "zone": zone,
            }
        )
    return tags


def _tank_level_series(n_steps: int, rng: random.Random) -> list[float]:
    base = rng.uniform(40, 70)
    amplitude = rng.uniform(5, 15)
    period = rng.uniform(n_steps / 3, n_steps)
    values = []
    for i in range(n_steps):
        wave = amplitude * math.sin(2 * math.pi * i / period)
        noise = rng.gauss(0, 1.0)
        values.append(min(100.0, max(0.0, base + wave + noise)))
    return values


def _pump_run_state_series(n_steps: int, rng: random.Random) -> list[float]:
    """Markov on/off process so runs form contiguous blocks, not noise."""
    p_turn_on = 0.03
    p_turn_off = 0.05
    state = 0
    values = []
    for _ in range(n_steps):
        if state == 0 and rng.random() < p_turn_on:
            state = 1
        elif state == 1 and rng.random() < p_turn_off:
            state = 0
        values.append(float(state))
    return values


def _flow_rate_series(n_steps: int, rng: random.Random) -> list[float]:
    baseline = rng.uniform(20, 120)
    values = []
    for _ in range(n_steps):
        noise = rng.gauss(0, baseline * 0.05)
        values.append(max(0.0, baseline + noise))
    return values


_SERIES_BY_KIND = {
    "tank_level": _tank_level_series,
    "pump_run_state": _pump_run_state_series,
    "flow_rate": _flow_rate_series,
}


def generate_readings(
    tags: list[dict],
    start_ts: int,
    end_ts: int,
    interval_s: int,
    rng: random.Random | None = None,
) -> list[tuple[str, int, float]]:
    """(tag_id, ts, value) rows for every tag across [start_ts, end_ts), one
    contiguous, evenly-spaced series per tag -- no gaps."""
    rng = rng or random.Random()
    if end_ts <= start_ts or interval_s <= 0:
        return []

    n_steps = (end_ts - start_ts) // interval_s
    rows = []
    for tag in tags:
        series_fn = _SERIES_BY_KIND[tag["kind"]]
        values = series_fn(n_steps, rng)
        for i, value in enumerate(values):
            rows.append((tag["node_id"], start_ts + i * interval_s, value))
    return rows


def seed(
    db_path: str | Path,
    hours: int = 6,
    interval_s: int = 60,
    end_ts: int | None = None,
    seed_value: int | None = None,
) -> int:
    """Create the DB, write the tag catalog, and backfill `hours` of
    readings ending at `end_ts` (default: now). Returns rows written."""
    import time

    rng = random.Random(seed_value)
    end_ts = end_ts if end_ts is not None else int(time.time())
    start_ts = end_ts - hours * 3600

    tags = generate_tags()
    readings = generate_readings(tags, start_ts, end_ts, interval_s, rng)

    conn = init_db(db_path)
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO tags (node_id, name, kind, unit, zone) "
            "VALUES (:node_id, :name, :kind, :unit, :zone)",
            tags,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO readings (tag_id, ts, value) VALUES (?, ?, ?)",
            readings,
        )
        conn.commit()
    finally:
        conn.close()
    return len(readings)


LINES = [
    {"id": "line-1", "name": "Line 1", "ideal_rate_per_hour": 120.0},
    {"id": "line-2", "name": "Line 2", "ideal_rate_per_hour": 90.0},
    {"id": "line-3", "name": "Line 3", "ideal_rate_per_hour": 150.0},
]


def generate_lines() -> list[dict]:
    return [dict(line) for line in LINES]


def generate_current_shift(line: dict, now_ts: int, rng: random.Random) -> dict:
    """One ongoing (ended_at=None) shift per line, 1-6 hours in."""
    duration_s = rng.randint(3600, 6 * 3600)
    return {
        "id": f"{line['id']}-current",
        "line_id": line["id"],
        "started_at": now_ts - duration_s,
        "ended_at": None,
    }


def generate_production_events(
    line: dict, shift: dict, now_ts: int, rng: random.Random
) -> list[tuple[str, int, str]]:
    """(shift_id, ts, event_type) rows for one ongoing shift: 0-2 downtime
    windows plus good/reject unit events spread across the shift so far.

    Unit events are spaced evenly across the whole shift window rather than
    only the non-downtime portions -- a known simplification, like
    widgets.SAMPLE_INTERVAL_S. It doesn't affect the OEE math (which counts
    events and downtime independently), only the visual evenness of the
    underlying event stream, which nothing here reads directly.
    """
    efficiency = rng.uniform(0.55, 0.95)  # actual rate as a fraction of ideal
    defect_rate = rng.uniform(0.02, 0.08)
    started_at = shift["started_at"]
    duration_s = now_ts - started_at

    events: list[tuple[str, int, str]] = []
    n_downtimes = rng.randint(0, 2)
    for _ in range(n_downtimes):
        if now_ts - started_at < 600:
            break
        dt_start = rng.randint(started_at, now_ts - 300)
        dt_end = min(dt_start + rng.randint(180, 1200), now_ts)
        events.append((shift["id"], dt_start, "downtime_start"))
        events.append((shift["id"], dt_end, "downtime_end"))

    downtime_s = sum(
        end - start for (_, start, _), (_, end, _) in zip(events[0::2], events[1::2])
    )
    run_s = max(duration_s - downtime_s, 0)
    actual_units_per_s = (line["ideal_rate_per_hour"] * efficiency) / 3600
    total_units = int(run_s * actual_units_per_s)

    for i in range(total_units):
        ts = started_at + int(i * duration_s / max(total_units, 1))
        event_type = "reject_unit" if rng.random() < defect_rate else "good_unit"
        events.append((shift["id"], ts, event_type))

    return events


def seed_mes(
    db_path: str | Path,
    end_ts: int | None = None,
    seed_value: int | None = None,
) -> int:
    """Create the DB, write the line catalog, and give each line one
    ongoing shift with synthetic production events. Returns rows written."""
    import time

    rng = random.Random(seed_value)
    end_ts = end_ts if end_ts is not None else int(time.time())
    lines = generate_lines()

    conn = init_db(db_path)
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO lines (id, name, ideal_rate_per_hour) "
            "VALUES (:id, :name, :ideal_rate_per_hour)",
            lines,
        )
        events_written = 0
        for line in lines:
            shift = generate_current_shift(line, end_ts, rng)
            conn.execute(
                "INSERT OR REPLACE INTO shifts (id, line_id, started_at, ended_at) "
                "VALUES (:id, :line_id, :started_at, :ended_at)",
                shift,
            )
            events = generate_production_events(line, shift, end_ts, rng)
            conn.executemany(
                "INSERT INTO production_events (shift_id, ts, event_type) VALUES (?, ?, ?)",
                events,
            )
            events_written += len(events)
        conn.commit()
    finally:
        conn.close()
    return events_written


# Every zone routes tank -> pump -> flow meter as a straight chain except
# this one, whose pump also feeds a second flow meter -- proof that the flow
# widget renders real divergence, not just a uniform path. Same lesson as
# mes-mcp's recall UI: a uniform path reads fine as a sentence; a genuine
# branch needs a diagram, and this zone exists so there's one to prove it on.
DIVERGENT_ZONE = "west"


def generate_divergent_tag(zone: str = DIVERGENT_ZONE) -> dict:
    """The one extra tag the divergent zone's second route needs. Deliberately
    a kind ('flow_rate_aux') that intent.py never matches for line/bar/stat --
    this tag exists only to be a flow-widget node, not a queryable series."""
    return {
        "node_id": f"{zone}.flow_rate_b",
        "name": f"{zone.title()} Auxiliary Flow Rate",
        "kind": "flow_rate_aux",
        "unit": "gpm",
        "zone": zone,
    }


def generate_routes(
    zones: list[str] = ZONES, divergent_zone: str = DIVERGENT_ZONE
) -> list[dict]:
    """(zone, from_tag, to_tag) rows: tank -> pump -> flow meter for every
    zone, plus pump -> the auxiliary flow meter for `divergent_zone` only."""
    routes = []
    for zone in zones:
        routes.append({"zone": zone, "from_tag": f"{zone}.tank_level", "to_tag": f"{zone}.pump_run_state"})
        routes.append({"zone": zone, "from_tag": f"{zone}.pump_run_state", "to_tag": f"{zone}.flow_rate"})
        if zone == divergent_zone:
            routes.append({
                "zone": zone, "from_tag": f"{zone}.pump_run_state", "to_tag": f"{zone}.flow_rate_b",
            })
    return routes


def seed_routes(db_path: str | Path) -> int:
    """Create the DB (if needed), add the divergent zone's auxiliary tag, and
    write the zone piping routes. Kept separate from seed()/seed_mes() the
    same way those are separate from each other -- this is flow-topology demo
    data, not telemetry or OEE, and keeping it isolated means seed()'s own
    tag count stays exactly "one per zone per kind" as its docstring promises.
    No readings are backfilled for the auxiliary tag; the flow widget only
    needs topology and tag names, not a value series. Returns routes written.
    """
    conn = init_db(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO tags (node_id, name, kind, unit, zone) "
            "VALUES (:node_id, :name, :kind, :unit, :zone)",
            generate_divergent_tag(),
        )
        routes = generate_routes()
        conn.executemany(
            "INSERT INTO routes (zone, from_tag, to_tag) VALUES (:zone, :from_tag, :to_tag)",
            routes,
        )
        conn.commit()
    finally:
        conn.close()
    return len(routes)


if __name__ == "__main__":
    load_dotenv()
    path = os.environ.get("SQLITE_PATH", "./data/telemetry.db")
    n = seed(path)
    print(f"Seeded {n} readings across {len(generate_tags())} tags into {path}")
    n_events = seed_mes(path)
    print(f"Seeded {n_events} production events across {len(LINES)} lines into {path}")
    n_routes = seed_routes(path)
    print(f"Seeded {n_routes} flow routes into {path}")
