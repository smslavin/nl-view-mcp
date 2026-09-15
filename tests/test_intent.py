from intent import understand_instruction

TAGS = [
    {"node_id": f"{zone}.{kind}", "name": zone, "kind": kind, "unit": "u", "zone": zone}
    for zone in ("north", "south", "east", "west")
    for kind in ("tank_level", "pump_run_state", "flow_rate")
]


def test_tank_level_trend_resolves_to_line_with_no_llm_needed():
    intent = understand_instruction("show me tank level trends for the last hour", TAGS)

    assert intent.kind == "tank_level"
    assert intent.chart_type == "line"
    assert intent.window_s == 3600
    assert intent.zones is None


def test_pump_run_hours_by_zone_resolves_to_bar():
    intent = understand_instruction("compare pump run hours by zone", TAGS)

    assert intent.kind == "pump_run_state"
    assert intent.chart_type == "bar"


def test_current_flow_rate_resolves_to_stat():
    intent = understand_instruction("what's the current flow rate", TAGS)

    assert intent.kind == "flow_rate"
    assert intent.chart_type == "stat"
    assert intent.window_s is None


def test_vague_instruction_with_no_kind_signal_is_left_unresolved():
    intent = understand_instruction("how's the west side looking", TAGS)

    assert intent.kind is None
    assert intent.chart_type is None
    assert intent.zones == ["west"]


def test_kind_matched_but_no_other_signal_is_left_unresolved():
    intent = understand_instruction("tell me about tank level", TAGS)

    assert intent.kind == "tank_level"
    assert intent.chart_type is None


def test_matching_is_case_insensitive():
    intent = understand_instruction("SHOW ME TANK LEVEL TRENDS FOR THE LAST HOUR", TAGS)
    assert intent.chart_type == "line"


def test_parses_explicit_minute_window():
    intent = understand_instruction("flow rate for the last 30 minutes", TAGS)
    assert intent.chart_type == "line"
    assert intent.window_s == 1800


def test_oee_by_line_resolves_to_bar():
    oee_tags = TAGS + [
        {
            "node_id": "oee.line-1",
            "name": "Line 1 OEE",
            "kind": "oee",
            "unit": "%",
            "zone": "line-1",
        }
    ]
    intent = understand_instruction("show OEE by line for the current shift", oee_tags)

    assert intent.kind == "oee"
    assert intent.chart_type == "bar"
