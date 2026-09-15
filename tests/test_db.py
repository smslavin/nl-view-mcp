from db import init_db
from generator import generate_tags, seed


def test_init_db_creates_expected_tables(tmp_path):
    conn = init_db(tmp_path / "telemetry.db")
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"tags", "readings"} <= tables
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    path = tmp_path / "telemetry.db"
    init_db(path).close()
    init_db(path).close()  # must not raise on re-init


def test_seed_writes_queryable_tags_and_readings(tmp_path):
    path = tmp_path / "telemetry.db"
    rows_written = seed(path, hours=1, interval_s=60, end_ts=3600, seed_value=7)

    conn = init_db(path)
    tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    reading_count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()

    assert tag_count == len(generate_tags())
    assert reading_count == rows_written
    assert reading_count == tag_count * 60  # 1 hour at 60s resolution


def test_seed_readings_are_scoped_to_the_requested_window(tmp_path):
    path = tmp_path / "telemetry.db"
    seed(path, hours=1, interval_s=60, end_ts=3600, seed_value=7)

    conn = init_db(path)
    min_ts, max_ts = conn.execute("SELECT MIN(ts), MAX(ts) FROM readings").fetchone()
    conn.close()

    assert min_ts >= 0
    assert max_ts < 3600
