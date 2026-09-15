import random

from generator import (
    LINES,
    ZONES,
    generate_current_shift,
    generate_production_events,
    generate_readings,
    generate_tags,
)


def test_generate_tags_covers_every_zone_and_kind():
    tags = generate_tags()

    assert len(tags) == len(ZONES) * 3
    kinds_by_zone = {}
    for tag in tags:
        kinds_by_zone.setdefault(tag["zone"], set()).add(tag["kind"])
    for zone in ZONES:
        assert kinds_by_zone[zone] == {"tank_level", "pump_run_state", "flow_rate"}


def test_generate_tags_node_ids_are_unique():
    tags = generate_tags()
    node_ids = [t["node_id"] for t in tags]
    assert len(node_ids) == len(set(node_ids))


def test_generate_readings_row_count_matches_steps_times_tags():
    tags = generate_tags()
    start_ts, end_ts, interval_s = 0, 3600, 60  # 1 hour at 1-minute resolution
    rows = generate_readings(tags, start_ts, end_ts, interval_s, random.Random(1))

    expected_steps = (end_ts - start_ts) // interval_s
    assert len(rows) == expected_steps * len(tags)


def test_generate_readings_has_no_gaps_per_tag():
    tags = generate_tags()
    start_ts, end_ts, interval_s = 1000, 1000 + 3600, 60
    rows = generate_readings(tags, start_ts, end_ts, interval_s, random.Random(2))

    by_tag: dict[str, list[int]] = {}
    for tag_id, ts, _value in rows:
        by_tag.setdefault(tag_id, []).append(ts)

    for tag in tags:
        timestamps = sorted(by_tag[tag["node_id"]])
        assert timestamps[0] == start_ts
        assert timestamps[-1] == start_ts + interval_s * (len(timestamps) - 1)
        deltas = {b - a for a, b in zip(timestamps, timestamps[1:])}
        assert deltas == {interval_s}


def test_generate_readings_values_stay_in_expected_range_per_kind():
    tags = generate_tags()
    rows = generate_readings(tags, 0, 3600 * 3, 60, random.Random(3))

    kind_by_id = {t["node_id"]: t["kind"] for t in tags}
    for tag_id, _ts, value in rows:
        kind = kind_by_id[tag_id]
        if kind == "tank_level":
            assert 0.0 <= value <= 100.0
        elif kind == "pump_run_state":
            assert value in (0.0, 1.0)
        elif kind == "flow_rate":
            assert value >= 0.0


def test_generate_readings_empty_when_window_is_empty():
    tags = generate_tags()
    assert generate_readings(tags, 100, 100, 60) == []
    assert generate_readings(tags, 200, 100, 60) == []


def test_generate_readings_is_deterministic_for_a_given_seed():
    tags = generate_tags()
    rows_a = generate_readings(tags, 0, 3600, 60, random.Random(42))
    rows_b = generate_readings(tags, 0, 3600, 60, random.Random(42))
    assert rows_a == rows_b


def test_generate_current_shift_is_open_ended_and_recent():
    now_ts = 100_000
    shift = generate_current_shift(LINES[0], now_ts, random.Random(1))

    assert shift["line_id"] == LINES[0]["id"]
    assert shift["ended_at"] is None
    assert 0 < now_ts - shift["started_at"] <= 6 * 3600


def test_generate_production_events_has_only_known_event_types():
    now_ts = 100_000
    shift = generate_current_shift(LINES[0], now_ts, random.Random(2))
    events = generate_production_events(LINES[0], shift, now_ts, random.Random(2))

    event_types = {event_type for _shift_id, _ts, event_type in events}
    assert event_types <= {"good_unit", "reject_unit", "downtime_start", "downtime_end"}
    assert len(events) > 0


def test_generate_production_events_downtime_windows_are_well_formed():
    now_ts = 100_000
    shift = generate_current_shift(LINES[0], now_ts, random.Random(3))
    events = generate_production_events(LINES[0], shift, now_ts, random.Random(3))

    downtime_events = [(t, ts) for _sid, ts, t in events if "downtime" in t]
    # they were appended in start/end pairs and each pair is chronological
    for start_evt, end_evt in zip(downtime_events[0::2], downtime_events[1::2]):
        assert start_evt[0] == "downtime_start"
        assert end_evt[0] == "downtime_end"
        assert start_evt[1] <= end_evt[1]
        assert shift["started_at"] <= start_evt[1] <= now_ts


def test_generate_production_events_all_timestamps_within_shift_window():
    now_ts = 100_000
    shift = generate_current_shift(LINES[1], now_ts, random.Random(4))
    events = generate_production_events(LINES[1], shift, now_ts, random.Random(4))

    for _shift_id, ts, _event_type in events:
        assert shift["started_at"] <= ts <= now_ts


def test_generate_production_events_is_deterministic_for_a_given_seed():
    now_ts = 100_000
    shift = generate_current_shift(LINES[0], now_ts, random.Random(5))
    events_a = generate_production_events(LINES[0], shift, now_ts, random.Random(5))
    events_b = generate_production_events(LINES[0], shift, now_ts, random.Random(5))
    assert events_a == events_b
