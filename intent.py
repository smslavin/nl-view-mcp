"""Chart-type heuristics.

Resolves a plain-English instruction against the discovered tag catalog into
an Intent -- which kind of tag, which zones, what time window, what chart
type -- using plain keyword/regex matching. No LLM involved here; this is
the "heuristic first" step described in the brief. `chart_type` is left
`None` when the heuristic can't confidently resolve it, which is the signal
build_view uses to fall back to the LLM classifier.
"""

import re
from dataclasses import dataclass

KIND_SYNONYMS = {
    "tank_level": ["tank level", "tank levels"],
    "pump_run_state": ["pump run hours", "pump run state", "pump run", "pump"],
    "flow_rate": ["flow rate", "flow"],
    "oee": ["oee", "overall equipment effectiveness"],
    "shift_history": ["shift history", "shifts"],
}

_GROUPING_PHRASES = ("by zone", "by line")
# "list"/"table" plus a matched kind means table. shift_history skips
# straight to table regardless of these words -- there's no sensible
# bar/line/stat rendering of a shift record.
_TABLE_WORDS = ("list", "table")
# Independent of `kind`: a flow query is about a zone's topology, not one
# tag's values.
_FLOW_PHRASES = ("flow diagram", "flow path", "flow topology", "routing", "topology", "flows to")

_TIME_UNIT_SECONDS = {"minute": 60, "minutes": 60, "hour": 3600, "hours": 3600}
_TIME_WINDOW_RE = re.compile(r"last\s+(\d+)?\s*(hour|hours|minute|minutes)\b")
_LATEST_WORDS = ("current", "currently", "right now")


@dataclass
class Intent:
    kind: str | None
    chart_type: str | None
    zones: list[str] | None = None
    window_s: int | None = None


def _parse_time_window(text: str) -> int | None:
    match = _TIME_WINDOW_RE.search(text)
    if not match:
        return None
    count = int(match.group(1)) if match.group(1) else 1
    return count * _TIME_UNIT_SECONDS[match.group(2)]


def _match_kind(text: str) -> str | None:
    for kind, synonyms in KIND_SYNONYMS.items():
        if any(synonym in text for synonym in synonyms):
            return kind
    return None


def _match_zones(text: str, tags: list[dict]) -> list[str] | None:
    zones = sorted({tag["zone"] for tag in tags})
    matched = [zone for zone in zones if zone in text]
    return matched or None


def understand_instruction(instruction: str, tags: list[dict]) -> Intent:
    text = instruction.lower()
    kind = _match_kind(text)
    zones = _match_zones(text, tags)
    window_s = _parse_time_window(text)
    group_by = any(phrase in text for phrase in _GROUPING_PHRASES)
    wants_latest = any(word in text for word in _LATEST_WORDS)
    wants_table = any(word in text for word in _TABLE_WORDS)
    wants_flow = any(phrase in text for phrase in _FLOW_PHRASES)

    chart_type = None
    if wants_flow:
        # Topology, not a tag's values -- resolves without a `kind` at all.
        chart_type = "flow"
    elif kind == "shift_history" or (kind is not None and wants_table):
        chart_type = "table"
    elif kind is not None:
        if group_by:
            chart_type = "bar"
        elif window_s is not None:
            chart_type = "line"
        elif wants_latest:
            chart_type = "stat"
        # Kind matched but none of the above signals fired: genuinely
        # ambiguous (e.g. "how's tank level"), left None for the LLM.

    return Intent(kind=kind, chart_type=chart_type, zones=zones, window_s=window_s)
