# nl-view-mcp

Viability prototype for a FieldWorks question: can a Knowi/ThoughtSpot-style
"one natural-language instruction builds a dashboard widget" pattern work as
an MCP-native, fieldworks-core consumer, using an MCP Apps-inspired `ui://`
resource as the declarative UI layer instead of agent-generated rendering
code?

This is a throwaway viability prototype, not production code. It is fully
standalone: no dependency on waterworks-ai or any live plant infrastructure.
Synthetic OPC-UA-shaped telemetry lives in a local SQLite file.

## Status

Scaffolding. See `bd ready` for the current build backlog.

## Design decisions worth knowing before reading the code

- **`ui://` is a naming convention here, not the literal MCP Apps spec.**
  The real [MCP Apps spec](https://github.com/modelcontextprotocol/ext-apps)
  serves HTML rendered in a sandboxed host iframe. This prototype instead
  registers `ui://` resources with `application/json` content — a declarative
  widget spec, read directly by a small bespoke Vue client. No HTML, no
  agent-generated code, ever reaches the client. Whether that divergence was
  the right call is one of the open questions this prototype exists to answer
  — see the findings section below once it's built.
- One MCP tool only: `build_view(instruction: str)`. Schema discovery and
  chart-type heuristics are internal steps inside that tool, not separate
  MCP tools an LLM has to sequence.
- Chart-type is decided by heuristic first (time series numeric -> line,
  categorical + counts -> bar, single scalar -> stat); an LLM call (Claude
  Haiku) is only a fallback for the ambiguous cases.

## Build order

1. [x] SQLite schema + synthetic telemetry data generator
2. [x] `build_view` tool: heuristics + query execution + `ui://` resource emission
3. [x] LLM fallback for heuristic-ambiguous instructions
4. [x] Vue + Chart.js renderer, wired to the live server
5. [x] Stretch: synthetic MES tables + an OEE-by-line instruction
6. [ ] Findings write-up (this README)

## Running it

```bash
uv sync
uv run python generator.py   # seeds ./data/telemetry.db: 6h of synthetic telemetry + MES lines/shifts
uv run pytest -q

uv run python server.py      # serves build_view over Streamable HTTP on :8010 (CORS open to :5173)
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173
npx vue-tsc --build
npx vitest run
```

`build_view` resolves these purely via heuristic, no LLM call:

- "show me tank level trends for the last hour" -> line
- "compare pump run hours by zone" -> bar
- "what's the current flow rate" -> stat
- "show OEE by line for the current shift" -> bar (synthetic MES tables --
  lines/shifts/production_events -- discovered as `oee`-kind pseudo-tags
  alongside the telemetry tag catalog; no other build_view changes)

An instruction with no kind keyword (e.g. "how's the west side looking") falls
through to the Claude Haiku classifier -- set `ANTHROPIC_API_KEY` for that path.

## Findings

Noted so far, final write-up next:

- **The widget spec has no semantic type for a point's `x` value.** Line
  charts always use Unix-seconds timestamps and bar charts always use
  categorical strings, but nothing in the schema says so -- the renderer
  guesses based on `chart_type` (see `chartData.ts`). The OEE-by-line bar
  chart hit the same gap from another angle: `x` is the raw line id
  (`line-1`), not the display name (`Line 1`), because the id is also the
  join key `widgets.py` needs for the SQL lookup -- the spec has nowhere to
  carry both an identifier and a display label. A real version of this
  schema needs an explicit axis type, not an inferred one.
