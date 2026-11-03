### results-small.json  (model eu.anthropic.claude-haiku-4-5-20251001-v1:0, 5 trials, catalog +0)

| Metric | MCP | REST | Delta |
|---|---|---|---|
| Success rate | 100.0% | 100.0% | +0.0%  |
| Avg total tokens | 2838 | 2867 | +1.0%  |
| Avg input tokens | 2705 | 2692 | -0.5% (REST leaner) |
| Avg output tokens | 133 | 175 | +31.6%  |
| Median latency (ms) | 2116 | 2070 | -2.2% (REST leaner) |
| Avg tool calls | 1.5 | 1.5 | +0.0%  |
| Avg round-trips | 2.5 | 2.5 | +0.0%  |
| Cache hits (304) | 0 | 5 | REST only |
| Avg wire bytes | 178 | 192 | +7.9%  |

```json
{
  "mcp": {
    "runs": 30,
    "success_pct": 100.0,
    "avg_total_tokens": 2838,
    "avg_input_tokens": 2705,
    "avg_output_tokens": 133,
    "p50_latency_ms": 2116,
    "avg_tool_calls": 1.5,
    "avg_turns": 2.5,
    "total_cache_hits": 0,
    "avg_wire_bytes": 178
  },
  "rest": {
    "runs": 30,
    "success_pct": 100.0,
    "avg_total_tokens": 2867,
    "avg_input_tokens": 2692,
    "avg_output_tokens": 175,
    "p50_latency_ms": 2070,
    "avg_tool_calls": 1.5,
    "avg_turns": 2.5,
    "total_cache_hits": 5,
    "avg_wire_bytes": 192
  }
}
```

### results-large.json  (model eu.anthropic.claude-haiku-4-5-20251001-v1:0, 5 trials, catalog +24)

| Metric | MCP | REST | Delta |
|---|---|---|---|
| Success rate | 100.0% | 100.0% | +0.0%  |
| Avg total tokens | 6558 | 4231 | -35.5% (REST leaner) |
| Avg input tokens | 6406 | 4038 | -37.0% (REST leaner) |
| Avg output tokens | 152 | 193 | +27.0%  |
| Median latency (ms) | 1996 | 1810 | -9.3% (REST leaner) |
| Avg tool calls | 1.67 | 1.67 | +0.0%  |
| Avg round-trips | 2.67 | 2.67 | +0.0%  |
| Cache hits (304) | 0 | 5 | REST only |
| Avg wire bytes | 187 | 200 | +7.0%  |

```json
{
  "mcp": {
    "runs": 30,
    "success_pct": 100.0,
    "avg_total_tokens": 6558,
    "avg_input_tokens": 6406,
    "avg_output_tokens": 152,
    "p50_latency_ms": 1996,
    "avg_tool_calls": 1.67,
    "avg_turns": 2.67,
    "total_cache_hits": 0,
    "avg_wire_bytes": 187
  },
  "rest": {
    "runs": 30,
    "success_pct": 100.0,
    "avg_total_tokens": 4231,
    "avg_input_tokens": 4038,
    "avg_output_tokens": 193,
    "p50_latency_ms": 1810,
    "avg_tool_calls": 1.67,
    "avg_turns": 2.67,
    "total_cache_hits": 5,
    "avg_wire_bytes": 200
  }
}
```


### Scenario 2: strict unfamiliar API  (model eu.anthropic.claude-haiku-4-5-20251001-v1:0, 6 trials)

| Metric | MCP | REST (terse contract) |
|---|---|---|
| Final success | 100% | 100% |
| First-call success | 100% | 0% |
| Malformed calls (total) | 0 | 30 |
| Avg tool calls | 1.00 | 2.00 |
| Avg round-trips | 2.00 | 3.00 |
| Avg total tokens | 1841 | 3041 |
| Median latency (ms) | 1720 | 3006 |


### Control: REST with the MCP JSON schemas in its contract  (model eu.anthropic.claude-haiku-4-5-20251001-v1:0, 5 trials, run 2026-11-03)

Suggested in the dev.to comments: if the token gap on the large surface comes from where the description sits, a REST contract carrying the same JSON schemas should stay cheap. If it comes from the format of the description, it should land next to MCP. `rest-schema` (`iface_rest_schema.py`) is the REST arm with every tool's exact name, description and inputSchema pasted into the contract, plus method and path. All three arms ran in the same session.

```
python runner.py --trials 5 --catalog 0  --ifaces mcp,rest,rest-schema --out results-3arm-small.json
python runner.py --trials 5 --catalog 24 --ifaces mcp,rest,rest-schema --out results-3arm-large.json
```

| Surface | Arm | Success | Avg input tokens | Avg total tokens | Avg round-trips | 304s |
|---|---|---|---|---|---|---|
| 6 ops | mcp | 100% | 2705 | 2840 | 2.50 | 0 |
| 6 ops | rest | 100% | 2692 | 2866 | 2.50 | 5 |
| 6 ops | rest-schema | 100% | 3550 | 3724 | 2.50 | 5 |
| 30 ops | mcp | 100% | 6406 | 6558 | 2.67 | 0 |
| 30 ops | rest | 100% | 4038 | 4223 | 2.67 | 5 |
| 30 ops | rest-schema | 100% | 7542 | 7745 | 2.67 | 5 |

Extra input tokens per Converse call when going from 6 to 30 operations (tasks whose turn count did not change, identical across those five tasks):

| Arm | Extra tokens per call |
|---|---|
| rest (terse contract lines) | +422 |
| mcp (native tool schemas) | +1307 |
| rest-schema (same schemas in the contract) | +1384 |

Reading: the system prompt and toolConfig are both re-sent on every stateless Converse call, so neither arm reads its description "once". With the same JSON schemas, REST costs as much as MCP per call (slightly more, because of the added paths and HTTP notes). The 35% gap in results-large.json comes from the density of the description, not from protocol or placement.


### Scenario 2 follow-up: which part of the schema buys first-call success?  (model eu.anthropic.claude-haiku-4-5-20251001-v1:0, 6 trials, run 2026-11-03)

Suggested in the dev.to comments. The terse REST contract is enriched one step at a time (`strict_curve.py`): first the enum lists only, then the date format, then the full JSON schema. First-call input tokens are measured with a single Converse call per arm on the same prompt.

```
python strict_runner.py --trials 6 --ifaces mcp,rest,rest-enums,rest-enums-date,rest-schema --out results-strict-curve.json
```

| Arm | First-call input tokens | First-call success | Malformed calls | Avg round-trips | Avg total tokens |
|---|---|---|---|---|---|
| rest (terse) | 730 | 0% | 30 | 3.00 | 3043 |
| rest-enums | 783 (+53) | 100% | 0 | 2.00 | 1885 |
| rest-enums-date | 795 (+65) | 100% | 0 | 2.00 | 1905 |
| rest-schema | 895 (+165) | 100% | 0 | 2.00 | 2103 |
| mcp | 784 | 100% | 0 | 2.00 | 1841 |

Reading: the enum values do all the work. 53 tokens of allowed values take first-call success from 0% to 100%; the date format, types and descriptions add tokens and nothing measurable on this API (the prompts already give dates as YYYY-MM-DD in most tasks). Terse contract plus enums costs the same per call as the MCP schema.
