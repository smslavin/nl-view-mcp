from intent import Intent
from widgets import build_bar_spec, build_line_spec, build_stat_spec, build_widget_spec


def test_build_line_spec_has_one_series_per_zone_with_points_in_window(
    seeded_conn, tags, freeze_now
):
    intent = Intent(kind="tank_level", chart_type="line", zones=None, window_s=3600)
    spec = build_line_spec(intent, tags, seeded_conn)

    assert spec["widget_type"] == "chart"
    assert spec["chart_type"] == "line"
    assert len(spec["series"]) == 4  # one per zone
    for series in spec["series"]:
        assert series["unit"] == "%"
        assert len(series["points"]) > 0
        for point in series["points"]:
            assert 0.0 <= point["y"] <= 100.0


def test_build_line_spec_scopes_to_requested_zones(seeded_conn, tags, freeze_now):
    intent = Intent(kind="flow_rate", chart_type="line", zones=["north"], window_s=1800)
    spec = build_line_spec(intent, tags, seeded_conn)

    assert len(spec["series"]) == 1
    assert "North" in spec["series"][0]["name"]


def test_build_bar_spec_has_one_point_per_zone(seeded_conn, tags):
    intent = Intent(kind="pump_run_state", chart_type="bar")
    spec = build_bar_spec(intent, tags, seeded_conn)

    assert spec["chart_type"] == "bar"
    points = spec["series"][0]["points"]
    zones = {p["x"] for p in points}
    assert zones == {"north", "south", "east", "west"}
    for point in points:
        assert point["y"] >= 0.0
    assert spec["series"][0]["unit"] == "hours"


def test_build_stat_spec_averages_latest_reading_across_matched_tags(seeded_conn, tags):
    intent = Intent(kind="flow_rate", chart_type="stat")
    spec = build_stat_spec(intent, tags, seeded_conn)

    assert spec["widget_type"] == "stat"
    point = spec["series"][0]["points"][0]
    assert point["x"] == "now"
    assert point["y"] >= 0.0
    assert spec["series"][0]["unit"] == "gpm"


def test_build_bar_spec_computes_oee_by_line(seeded_conn, tags, freeze_now):
    intent = Intent(kind="oee", chart_type="bar")
    spec = build_bar_spec(intent, tags, seeded_conn)

    assert spec["title"] == "OEE by Line"
    points = spec["series"][0]["points"]
    lines = {p["x"] for p in points}
    assert lines == {"line-1", "line-2", "line-3"}
    for point in points:
        assert 0.0 <= point["y"] <= 100.0
    assert spec["series"][0]["unit"] == "%"


def test_build_bar_spec_oee_is_zero_for_a_line_with_no_open_shift(
    seeded_conn, tags, freeze_now
):
    seeded_conn.execute("UPDATE shifts SET ended_at = 999999 WHERE line_id = 'line-1'")
    intent = Intent(kind="oee", chart_type="bar")

    spec = build_bar_spec(intent, tags, seeded_conn)

    points = {p["x"]: p["y"] for p in spec["series"][0]["points"]}
    assert points["line-1"] == 0.0


def test_build_widget_spec_dispatches_on_chart_type(seeded_conn, tags, freeze_now):
    line_intent = Intent(kind="tank_level", chart_type="line", window_s=3600)
    bar_intent = Intent(kind="pump_run_state", chart_type="bar")
    stat_intent = Intent(kind="flow_rate", chart_type="stat")

    assert build_widget_spec(line_intent, tags, seeded_conn)["chart_type"] == "line"
    assert build_widget_spec(bar_intent, tags, seeded_conn)["chart_type"] == "bar"
    assert build_widget_spec(stat_intent, tags, seeded_conn)["chart_type"] == "stat"
