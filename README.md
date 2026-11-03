# mcp-vs-rest-bench

A measured head-to-head between a **stateless MCP server** and a **plain REST API**
serving the *same* backend to the *same* agent on the *same* tasks.

Companion to the blog post
[*"Is stateless MCP just REST? I ran 180 tests to find out"*](https://edoardodusi.com/blog/2026/mcp-vs-rest-measured.html)
on edoardodusi.com.

The question comes from the 2026-07-28 MCP spec, which
[removed protocol-level sessions](https://modelcontextprotocol.io/specification/2026-07-28/changelog).
If a tool server is now just stateless HTTP, is MCP just REST with extra steps?
This harness answers it with data instead of taste.

## What it does

One deterministic backend (`backend.py`) is exposed through two interfaces over
the **same six operations**:

- `iface_mcp.py`: operations as native tool-use schemas on Amazon Bedrock's
  Converse API. This is what a stateless MCP server reduces to on the wire:
  tool names plus JSON schemas presented to the model every turn.
- `iface_rest.py`: a single `http_request` tool plus a terse OpenAPI-style
  contract in the system prompt, one line per endpoint, with a real `ETag` /
  `304 Not Modified` cache so conditional reads can be measured.
- `iface_rest_schema.py` (control arm, `rest-schema`): the same REST interface,
  but the contract carries the MCP arm's exact JSON schema for every endpoint.
  It separates the protocol from the format of the description.

Converse is stateless and the harness uses no prompt caching, so the system
prompt (REST contract) and `toolConfig` (MCP schemas) are both re-sent on
every call. Neither arm reads its description only once.

The same agent loop (`runner.py`) runs all arms against the same task suite
(`tasks.py`) and records success, tokens, latency, round-trips, tool calls and
cache hits. `distractors.py` scales the API surface so you can see how the
per-call cost of each description format grows with it.

## Architecture

```mermaid
flowchart LR
    subgraph Harness["Benchmark harness (local Python)"]
        T[Task suite] --> L[Shared agent loop]
        L -->|toolConfig: N schemas/turn| M[MCP interface]
        L -->|1 http_request tool + contract/turn| R[REST interface]
        L -->|1 http_request tool + schema contract/turn| S[REST-schema interface]
        M --> B[(Deterministic<br/>store backend)]
        R --> B
        S --> B
        R -.ETag / 304.-> L
    end
    L <-->|Converse API| BR["Amazon Bedrock<br/>Claude Haiku 4.5<br/>eu-central-1"]
    L --> J[results-*.json]
    J --> A[analyze.py]
```

## Run it

```bash
# Prereqs: Python 3.11+, AWS credentials with Bedrock access, model enabled.
export AWS_PROFILE=your-sandbox-profile   # needs bedrock:InvokeModel
python3 -m venv .venv && . .venv/bin/activate
pip install boto3

# Small API surface (6 tools): MCP and REST tie.
python runner.py --trials 5 --catalog 0  --out results-small.json

# Large API surface (30 tools): MCP spends more tokens per call.
python runner.py --trials 5 --catalog 24 --out results-large.json

# Aggregate into markdown tables.
python analyze.py results-small.json results-large.json

# Control: add the REST arm with the MCP schemas in its contract.
python runner.py --trials 5 --catalog 0  --ifaces mcp,rest,rest-schema --out results-3arm-small.json
python runner.py --trials 5 --catalog 24 --ifaces mcp,rest,rest-schema --out results-3arm-large.json
```

Flags: `--model` (default `eu.anthropic.claude-haiku-4-5-20251001-v1:0`),
`--region` (default `eu-central-1`), `--trials`, `--catalog`, `--out`,
`--ifaces` (default `mcp,rest`; add `rest-schema` for the control arm).

### Scenario 2: where MCP wins (strict unfamiliar API)

Scenario 1 above is REST's turf (per-request efficiency). Scenario 2 is MCP's:
a strict analytics API with non-guessable enum values and formats. MCP gets its
normal typed tool schema (enums enumerated, host validates the call). REST gets
a realistic *terse* human contract that names the params but not every enum.

```bash
python strict_runner.py --trials 6 --out results-strict.json
```

`strict_backend.py` + `strict_scenario.py` + `strict_runner.py`.

## Headline results

See `RESULTS.md` for the full tables. In short, measured on Claude Haiku 4.5,
`eu-central-1`, 5 trials:

- **Small surface (6 tools):** tie. 100% success both, tokens within ~1%, same
  round-trips. REST's only edge is caching.
- **Large surface (30 tools):** same success and round-trips, but MCP spends
  **~35% more total tokens** and **~37% more input tokens**. Both arms re-send
  their description on every call; a JSON tool schema simply costs about three
  times a one-line contract entry.
- **Control (REST with the MCP schemas):** going from 6 to 30 operations adds
  **+422** input tokens per call for terse REST, **+1,307** for MCP and
  **+1,384** for REST with the same schemas. The gap comes from the density of
  the description, not from the protocol or where the description sits.
  (Suggested by a reader in the post's comments.)
- **Caching:** REST scores 5/5 conditional-read cache hits (`If-None-Match` ->
  `304`); MCP tool use has no standard conditional read, so 0/5.
- **Strict unfamiliar API (scenario 2):** both reach 100% final success, but MCP
  is correct on the **first** call 100% of the time vs **0%** for the terse-contract
  REST agent, which guesses an enum wrong, eats a `400`, and self-corrects. MCP
  uses half the tool calls, ~65% fewer tokens and ~75% lower latency. Typed,
  validated discovery is MCP's structural win. (You *can* close the gap by pasting
  full JSON Schema into the REST contract, but the control run shows that costs
  as many tokens per call as MCP. The schema has to live somewhere.)

Your numbers will differ with model, prompt caching and tool filtering. That is
the point: rerun it on your own stack.

## Cost

The harness creates **no persistent AWS resources**. It only calls Bedrock
on-demand (`InvokeModel` via Converse). A full sweep is two conditions x six
tasks x two interfaces x five trials = 120 runs, a few thousand tokens each.
The three-arm control adds 180 runs.

At Claude Haiku 4.5 on-demand pricing this is a few cents per full sweep. Check
current pricing on the [Amazon Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/);
do not trust a number hard-coded in a README.

## Teardown

There is nothing to tear down. No infrastructure is provisioned: no endpoints,
no roles, no storage, no standing compute. Bedrock on-demand billing stops the
moment the script exits. To clean up locally:

```bash
deactivate 2>/dev/null; rm -rf .venv results-*.json
```

## Limits (read before quoting a number)

One model, one small domain, six tasks, no auth / streaming / human-in-the-loop.
"Wire bytes" is a proxy, not a packet capture. This measures per-request
efficiency, which is **not** MCP's main selling point (ecosystem portability is).
It is one axis of a trade-off, not a verdict.

## License

MIT.
