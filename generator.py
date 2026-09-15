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


if __name__ == "__main__":
    load_dotenv()
    path = os.environ.get("SQLITE_PATH", "./data/telemetry.db")
    n = seed(path)
    print(f"Seeded {n} readings across {len(generate_tags())} tags into {path}")
