import json

import pytest

from llm_fallback import classify_with_llm

TAGS = [{"node_id": "west.tank_level", "name": "West Tank Level", "kind": "tank_level", "unit": "%", "zone": "west"}]


class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, payload: dict):
        self.content = [_FakeContentBlock(json.dumps(payload))]


class _FakeMessages:
    def __init__(self, payload: dict):
        self._payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._payload)


class _FakeClient:
    def __init__(self, payload: dict):
        self.messages = _FakeMessages(payload)


def test_classify_with_llm_parses_a_valid_response():
    client = _FakeClient(
        {"kind": "tank_level", "chart_type": "line", "zones": ["west"], "window_s": 3600}
    )

    intent = classify_with_llm("how's the west side looking", TAGS, client=client)

    assert intent.kind == "tank_level"
    assert intent.chart_type == "line"
    assert intent.zones == ["west"]
    assert intent.window_s == 3600


def test_classify_with_llm_passes_instruction_and_schema_to_the_model():
    client = _FakeClient({"kind": "tank_level", "chart_type": "stat", "zones": None, "window_s": None})

    classify_with_llm("how's the west side looking", TAGS, client=client)

    call = client.messages.calls[0]
    assert "how's the west side looking" in call["messages"][0]["content"]
    assert "tank_level" in call["messages"][0]["content"]


def test_classify_with_llm_rejects_unknown_kind():
    client = _FakeClient({"kind": "not_a_real_kind", "chart_type": "line", "zones": None, "window_s": 3600})

    with pytest.raises(ValueError, match="unknown kind"):
        classify_with_llm("anything", TAGS, client=client)


def test_classify_with_llm_rejects_unknown_chart_type():
    client = _FakeClient({"kind": "tank_level", "chart_type": "pie", "zones": None, "window_s": None})

    with pytest.raises(ValueError, match="unknown chart_type"):
        classify_with_llm("anything", TAGS, client=client)
