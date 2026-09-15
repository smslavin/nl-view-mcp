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

Prototype complete. See Findings below for the viability verdict.

## Design decisions worth knowing before reading the code

- **`ui://` is a naming convention here, not the literal MCP Apps spec.**
  The real [MCP Apps spec](https://github.com/modelcontextprotocol/ext-apps)
  serves HTML rendered in a sandboxed host iframe. This prototype instead
  registers `ui://` resources with `application/json` content — a declarative
  widget spec, read directly by a small bespoke Vue client. No HTML, no
  agent-generated code, ever reaches the client. Whether that divergence was
  the right call is answered in Findings below (short version: marginal,
  leaning no, for a payload this small).
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
6. [x] Findings write-up (this README)

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

**Verdict: the pattern holds up, and is worth building for real** -- with two
concrete fixes to carry forward (below) rather than as a wholesale redesign.
The strongest evidence is the MES stretch goal: getting from tank levels to
"OEE by line" took one new discovery function and two one-line additions to
`intent.py`. Nothing about `build_view`'s discover -> heuristic -> query ->
emit shape had to change. That's the property the whole prototype existed to
test, and it survived contact with a genuinely different domain.

### Where the chart-type heuristics got it wrong (or got lucky)

They resolved all four example instructions correctly, three without ever
calling an LLM. But that's a narrower result than it sounds:

- **The heuristics are a fixed phrasing list, not language understanding.**
  Grouping detection only fires on the literal substrings "by zone" / "by
  line"; "compare across zones" or "per line" would silently miss and fall
  through to the LLM. Time windows only parse "last N hour(s)/minute(s)" --
  "since this morning" doesn't resolve. That's an acceptable shape for a
  small, operator-facing instruction vocabulary that gets reused constantly
  (which is realistic for a plant HMI), but it's a keyword router wearing a
  heuristic's clothes, not a general fallback-avoidance strategy.
- **The bigger risk is confident wrongness, not visible ambiguity.**
  `_match_kind` is first-match-wins over `KIND_SYNONYMS`. An instruction
  naming two kinds ("show tank level and flow rate together") would silently
  produce a single-kind chart instead of surfacing the ambiguity -- the
  "fall back to the LLM" safety net only catches the *no kind matched* case,
  not the *wrong kind matched confidently* case. This never came up in the
  four examples because none of them are multi-kind, which is itself the
  finding: the heuristic's blind spots are invisible until you instruct
  outside the set it was tuned against.
- The one deliberately-ambiguous instruction we exercised ("how's the west
  side looking") worked, but that's one data point on the LLM fallback path,
  not a stress test of it.

### Was `ui://` the right layer?

Mechanically, yes -- it worked. Was it worth it? **Marginal, leaning no**,
for this design specifically. The JSON-native, spec-adjacent `ui://`
resource added a second MCP round trip (`resources/read` after
`tools/call`) plus a slug/store bookkeeping layer (`_VIEW_STORE`, slug
generation in `server.py`) that bought nothing the client couldn't get from
the tool's return value directly. The client already knew how to render the
spec the moment it had it; resource-level indirection didn't add capability
or safety on top of that.

`ui://`'s real justification in the actual MCP Apps spec is that the
resource is genuinely decoupled content -- HTML/JS a generic host fetches,
sandboxes, and mounts independently of the tool call that triggered it.
None of that applies to a small JSON blob one bespoke client consumes once
and never re-fetches. The one thing URI-addressability gives for free --
a stable handle a second client could re-read, or a specific widget could be
refreshed by URI without re-running `build_view` -- never came up in a
single-session prototype, but it's the one scenario where this would start
to earn its keep.

**Recommendation:** for a pure-JSON widget spec, return it as the tool's
structured result and skip `ui://` entirely, unless there's a concrete
multi-client or independent-refresh requirement. Reserve `ui://` for the
case it was actually designed for: content a generic host needs to sandbox.

### Schema gap: no semantic type for a point's `x` value

Found twice, same root cause. Line charts always use Unix-seconds
timestamps and bar charts always use categorical strings, but nothing in
the schema says so -- `chartData.ts` guesses based on `chart_type`. The
OEE-by-line bar chart hit it from another angle: `x` is the raw line id
(`line-1`), not the display name (`Line 1`), because the id doubles as the
SQL join key `widgets.py` needs and the spec has nowhere to carry both an
identifier and a display label. A real version of this schema needs an
explicit axis type and an id/label split, not client-side inference.

### Two smaller things worth knowing if this gets built for real

- **MCP transport is still moving.** `SSEClientTransport` was already
  deprecated by the TypeScript SDK partway through this build, forcing a
  switch to Streamable HTTP on the server. Expect more of this from an
  ecosystem this young.
- **CORS is entirely unsolved by the SDK's high-level `mcp.run()`.** Any
  browser-facing MCP client has to drop to the raw ASGI app
  (`mcp.streamable_http_app()`) and wrap it manually -- a rough edge for the
  "MCP-native browser app" pattern generally, not specific to this
  prototype.
