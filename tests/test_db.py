from db import discover_mes, init_db
from generator import LINES, generate_tags, seed, seed_mes


def test_init_db_creates_expected_tables(tmp_path):
    conn = init_db(tmp_path / "telemetry.db")
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"tags", "readings", "lines", "shifts", "production_events"} <= tables
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


def test_seed_mes_writes_lines_shifts_and_events(tmp_path):
    path = tmp_path / "telemetry.db"
    events_written = seed_mes(path, end_ts=100_000, seed_value=1)

    conn = init_db(path)
    line_count = conn.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
    shift_count = conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM production_events").fetchone()[0]
    conn.close()

    assert line_count == len(LINES)
    assert shift_count == len(LINES)  # one open shift per line
    assert event_count == events_written
    assert event_count > 0


def test_discover_mes_returns_one_oee_pseudo_tag_per_line(tmp_path):
    path = tmp_path / "telemetry.db"
    seed_mes(path, end_ts=100_000, seed_value=1)

    conn = init_db(path)
    oee_tags = discover_mes(conn)
    conn.close()

    assert len(oee_tags) == len(LINES)
    for tag in oee_tags:
        assert tag["kind"] == "oee"
        assert tag["unit"] == "%"
        assert tag["zone"] in {line["id"] for line in LINES}
