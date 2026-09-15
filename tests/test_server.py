import json

import pytest

import server
from intent import Intent


def test_run_build_view_resolves_via_heuristic_without_calling_llm(
    seeded_conn, freeze_now
):
    def _llm_should_not_be_called(instruction, tags):
        raise AssertionError("heuristic should have resolved this instruction")

    spec = server.run_build_view(
        "show me tank level trends for the last hour",
        seeded_conn,
        _llm_should_not_be_called,
    )

    assert spec["chart_type"] == "line"


def test_run_build_view_falls_back_to_llm_when_heuristic_is_unresolved(seeded_conn):
    def _stub_llm(instruction, tags):
        return Intent(kind="tank_level", chart_type="stat", zones=["west"])

    spec = server.run_build_view("how's the west side looking", seeded_conn, _stub_llm)

    assert spec["chart_type"] == "stat"


def test_run_build_view_resolves_oee_by_line_without_calling_llm(
    seeded_conn, freeze_now
):
    def _llm_should_not_be_called(instruction, tags):
        raise AssertionError("heuristic should have resolved this instruction")

    spec = server.run_build_view(
        "show OEE by line for the current shift", seeded_conn, _llm_should_not_be_called
    )

    assert spec["chart_type"] == "bar"
    assert spec["title"] == "OEE by Line"


def test_build_view_then_get_view_round_trips_through_the_ui_resource(
    monkeypatch, tmp_path
):
    from generator import seed

    db_path = tmp_path / "telemetry.db"
    seed(db_path, hours=1, interval_s=60, end_ts=10_000_000, seed_value=1)
    monkeypatch.setattr(server, "SQLITE_PATH", str(db_path))

    result = json.loads(server.build_view("what's the current flow rate"))
    assert result["uri"].startswith("ui://view/")

    slug = result["uri"].removeprefix("ui://view/")
    spec = json.loads(server.get_view(slug))
    assert spec["widget_type"] == "stat"


def test_get_view_raises_for_an_unknown_slug():
    with pytest.raises(ValueError, match="Unknown view"):
        server.get_view("does-not-exist")
