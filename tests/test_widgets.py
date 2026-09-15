from generator import DIVERGENT_ZONE
from intent import Intent
from widgets import (
    build_bar_spec,
    build_flow_spec,
    build_line_spec,
    build_stat_spec,
    build_table_spec,
    build_widget_spec,
)


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
    table_intent = Intent(kind="shift_history", chart_type="table")
    flow_intent = Intent(kind=None, chart_type="flow")

    assert build_widget_spec(line_intent, tags, seeded_conn)["chart_type"] == "line"
    assert build_widget_spec(bar_intent, tags, seeded_conn)["chart_type"] == "bar"
    assert build_widget_spec(stat_intent, tags, seeded_conn)["chart_type"] == "stat"
    assert build_widget_spec(table_intent, tags, seeded_conn)["chart_type"] == "table"
    assert build_widget_spec(flow_intent, tags, seeded_conn)["chart_type"] == "flow"


# --- table ---------------------------------------------------------------------

def test_build_table_spec_has_one_row_per_line_with_typed_columns(seeded_conn, tags):
    intent = Intent(kind="shift_history", chart_type="table")
    spec = build_table_spec(intent, tags, seeded_conn)

    assert spec["widget_type"] == "table"
    assert spec["chart_type"] == "table"
    assert [c["key"] for c in spec["columns"]] == ["line", "started", "ended", "id"]
    assert next(c for c in spec["columns"] if c["key"] == "id")["kind"] == "code"
    assert len(spec["rows"]) == 3  # one open shift per line, per seed_mes
    for row in spec["rows"]:
        assert row["ended"] == "in progress"  # seed_mes only writes open shifts
        assert set(row.keys()) == {"line", "started", "ended", "id"}


# --- flow ---------------------------------------------------------------------

def test_build_flow_spec_uniform_zone_is_a_straight_three_node_chain(seeded_conn, tags):
    intent = Intent(kind=None, chart_type="flow", zones=["north"])
    spec = build_flow_spec(intent, tags, seeded_conn)

    assert spec["widget_type"] == "flow"
    assert spec["chart_type"] == "flow"
    node_ids = {n["id"] for n in spec["nodes"]}
    assert node_ids == {"north.tank_level", "north.pump_run_state", "north.flow_rate"}
    edges = {(e["from"], e["to"]) for e in spec["edges"]}
    assert edges == {
        ("north.tank_level", "north.pump_run_state"),
        ("north.pump_run_state", "north.flow_rate"),
    }
    # Node labels resolve from the tag catalog, not the raw node id.
    labels = {n["id"]: n["label"] for n in spec["nodes"]}
    assert labels["north.tank_level"] == "North Tank Level"


def test_build_flow_spec_divergent_zone_pump_has_two_outgoing_edges(seeded_conn, tags):
    intent = Intent(kind=None, chart_type="flow", zones=[DIVERGENT_ZONE])
    spec = build_flow_spec(intent, tags, seeded_conn)

    from_pump = {e["to"] for e in spec["edges"] if e["from"] == f"{DIVERGENT_ZONE}.pump_run_state"}
    assert from_pump == {f"{DIVERGENT_ZONE}.flow_rate", f"{DIVERGENT_ZONE}.flow_rate_b"}
    node_ids = {n["id"] for n in spec["nodes"]}
    assert f"{DIVERGENT_ZONE}.flow_rate_b" in node_ids


def test_build_flow_spec_with_no_zone_named_covers_every_zone(seeded_conn, tags):
    intent = Intent(kind=None, chart_type="flow", zones=None)
    spec = build_flow_spec(intent, tags, seeded_conn)

    zones_covered = {n["id"].split(".")[0] for n in spec["nodes"]}
    assert zones_covered == {"north", "south", "east", "west"}
    assert spec["title"] == "Flow Topology"  # no zone named -> no zone suffix
