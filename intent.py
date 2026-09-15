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
}

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
    group_by_zone = "by zone" in text
    wants_latest = any(word in text for word in _LATEST_WORDS)

    chart_type = None
    if kind is not None:
        if group_by_zone:
            chart_type = "bar"
        elif window_s is not None:
            chart_type = "line"
        elif wants_latest:
            chart_type = "stat"
        # Kind matched but none of the above signals fired: genuinely
        # ambiguous (e.g. "how's tank level"), left None for the LLM.

    return Intent(kind=kind, chart_type=chart_type, zones=zones, window_s=window_s)
