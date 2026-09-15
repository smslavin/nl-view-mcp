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
2. [ ] `build_view` tool: heuristics + query execution + `ui://` resource emission
3. [ ] LLM fallback for heuristic-ambiguous instructions
4. [ ] Vue + Chart.js renderer, wired to the live server
5. [ ] Stretch: synthetic MES tables + an OEE-by-line instruction
6. [ ] Findings write-up (this README)

## Running it

```bash
uv sync
uv run python generator.py   # seeds ./data/telemetry.db with 6h of synthetic readings
uv run pytest -q
```

The MCP server itself (`build_view`) is not runnable yet — comes online at step 2.

## Findings

(To be filled in after the prototype is built: what the chart-type heuristics
got wrong, and whether `ui://` felt like the right layer vs. just returning
structured data and letting the client decide.)
