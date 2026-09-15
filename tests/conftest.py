import time

import pytest

from db import discover_mes, discover_schema, init_db
from generator import seed, seed_mes

SEED_END_TS = 10_000_000  # arbitrary fixed "now" so window queries are deterministic


@pytest.fixture
def seeded_conn(tmp_path):
    path = tmp_path / "telemetry.db"
    seed(path, hours=2, interval_s=60, end_ts=SEED_END_TS, seed_value=42)
    seed_mes(path, end_ts=SEED_END_TS, seed_value=42)
    conn = init_db(path)
    yield conn
    conn.close()


@pytest.fixture
def tags(seeded_conn):
    return discover_schema(seeded_conn) + discover_mes(seeded_conn)


@pytest.fixture
def freeze_now(monkeypatch):
    """widgets.py windows queries off time.time(); pin it to line up with
    seeded_conn's fixed end_ts so 'last hour' actually covers seeded data."""
    monkeypatch.setattr(time, "time", lambda: float(SEED_END_TS))
