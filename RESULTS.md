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
