"""Aggregate results.json files into per-interface summaries.

Usage: python analyze.py results-small.json results-large.json
Prints a markdown table per input file plus an overall comparison.
"""
from __future__ import annotations
import json, sys, statistics


def summarize(path):
    data = json.load(open(path))
    rows = data["rows"]
    out = {}
    for iface in ("mcp", "rest"):
        r = [x for x in rows if x["iface"] == iface]
        n = len(r)
        succ = sum(x["success"] for x in r)
        out[iface] = {
            "runs": n,
            "success_pct": round(100 * succ / n, 1),
            "avg_total_tokens": round(statistics.mean(x["total_tokens"] for x in r)),
            "avg_input_tokens": round(statistics.mean(x["input_tokens"] for x in r)),
            "avg_output_tokens": round(statistics.mean(x["output_tokens"] for x in r)),
            "p50_latency_ms": round(statistics.median(x["latency_ms"] for x in r)),
            "avg_tool_calls": round(statistics.mean(x["tool_calls"] for x in r), 2),
            "avg_turns": round(statistics.mean(x["turns"] for x in r), 2),
            "total_cache_hits": sum(x["cache_hits"] for x in r),
            "avg_wire_bytes": round(statistics.mean(x["wire_bytes"] for x in r)),
        }
    return data, out


def md_table(label, data, s):
    cat = data.get("catalog", 0)
    lines = [f"### {label}  (model {data['model']}, {data['trials']} trials, catalog +{cat})", ""]
    lines.append("| Metric | MCP | REST | Delta |")
    lines.append("|---|---|---|---|")
    def row(name, key, fmt="{}", better="low"):
        m, re_ = s["mcp"][key], s["rest"][key]
        if isinstance(m, (int, float)) and m:
            d = round(100 * (re_ - m) / m, 1)
            delta = f"{d:+}% " + ("(REST leaner)" if (d < 0) == (better == "low") and d != 0 else "")
        else:
            delta = ""
        lines.append(f"| {name} | {fmt.format(m)} | {fmt.format(re_)} | {delta} |")
    row("Success rate", "success_pct", "{}%", "high")
    row("Avg total tokens", "avg_total_tokens")
    row("Avg input tokens", "avg_input_tokens")
    row("Avg output tokens", "avg_output_tokens")
    row("Median latency (ms)", "p50_latency_ms")
    row("Avg tool calls", "avg_tool_calls")
    row("Avg round-trips", "avg_turns")
    lines.append(f"| Cache hits (304) | {s['mcp']['total_cache_hits']} | {s['rest']['total_cache_hits']} | REST only |")
    row("Avg wire bytes", "avg_wire_bytes")
    return "\n".join(lines)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        data, s = summarize(p)
        print(md_table(p, data, s))
        print()
        print("```json")
        print(json.dumps(s, indent=2))
        print("```")
        print()
