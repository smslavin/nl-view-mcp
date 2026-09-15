"""LLM fallback for instructions the heuristic can't resolve.

Claude only ever picks from the same small, fixed enum the heuristic path
uses (kind, chart_type, zones, window_s) -- it never generates widget JSON
or any executable code. Kept as a thin classification call, not a
generation step.
"""

import json
import os

from anthropic import Anthropic

from intent import KIND_SYNONYMS, Intent

MODEL = "claude-haiku-4-5-20251001"

_CHART_TYPES = ("line", "bar", "stat")

_SYSTEM_PROMPT = """You classify a plant-operator instruction against a fixed schema.
Given the instruction and the available tags, respond with ONLY a JSON object, no \
prose and no markdown fences:

{"kind": one of "tank_level" | "pump_run_state" | "flow_rate",
 "chart_type": one of "line" | "bar" | "stat",
 "zones": a JSON list of zone names to scope to, or null for all zones,
 "window_s": integer seconds of history to show if chart_type is "line", else null}"""


def classify_with_llm(
    instruction: str, tags: list[dict], client: Anthropic | None = None
) -> Intent:
    client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    schema_summary = sorted({(tag["kind"], tag["zone"]) for tag in tags})

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Instruction: {instruction!r}\nAvailable (kind, zone) tags: {schema_summary}",
            }
        ],
    )
    parsed = json.loads(response.content[0].text)

    kind = parsed["kind"]
    if kind not in KIND_SYNONYMS:
        raise ValueError(f"LLM returned unknown kind: {kind!r}")
    chart_type = parsed["chart_type"]
    if chart_type not in _CHART_TYPES:
        raise ValueError(f"LLM returned unknown chart_type: {chart_type!r}")

    return Intent(
        kind=kind,
        chart_type=chart_type,
        zones=parsed.get("zones"),
        window_s=parsed.get("window_s"),
    )
