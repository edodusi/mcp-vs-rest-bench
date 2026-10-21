"""Benchmark runner: same agent loop, swapped interface, metrics per run.

Metrics captured per (interface, task, trial):
  success        grader passed
  turns          number of agent<->tool round-trips (assistant messages)
  input_tokens   summed over all Converse calls
  output_tokens  summed over all Converse calls
  total_tokens   input+output
  latency_ms     wall clock for the whole task
  tool_calls     number of tool_use blocks the model emitted
  wire_bytes     response-body bytes the interface returned
  cache_hits     REST 304s (0 for MCP)

Run:  python runner.py --trials 5 --model eu.anthropic.claude-haiku-4-5-20251001-v1:0
"""
from __future__ import annotations
import argparse, json, time, statistics, sys
import boto3
from botocore.config import Config

from backend import Backend
from iface_mcp import McpInterface
from iface_rest import RestInterface
from tasks import TASKS

MAX_TURNS = 8


def run_task(client, model, iface, task):
    messages = [{"role": "user", "content": [{"text": task["prompt"]}]}]
    in_tok = out_tok = turns = tool_calls = 0
    t0 = time.time()
    final_text = ""
    for _ in range(MAX_TURNS):
        resp = client.converse(
            modelId=model,
            system=[{"text": iface.system()}],
            messages=messages,
            toolConfig={"tools": iface.tools()},
            inferenceConfig={"maxTokens": 700, "temperature": 0},
        )
        turns += 1
        u = resp["usage"]
        in_tok += u["inputTokens"]
        out_tok += u["outputTokens"]
        out_msg = resp["output"]["message"]
        messages.append(out_msg)
        stop = resp["stopReason"]

        if stop == "tool_use":
            tool_results = []
            for block in out_msg["content"]:
                if "toolUse" not in block:
                    continue
                tu = block["toolUse"]
                tool_calls += 1
                result = iface.dispatch(tu["name"], tu.get("input") or {})
                tool_results.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"json": result["payload"]}],
                    "status": "success" if result["ok"] else "error",
                }})
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn
        for block in out_msg["content"]:
            if "text" in block:
                final_text += block["text"] + " "
        break

    latency_ms = int((time.time() - t0) * 1000)
    success = bool(task["grade"](final_text, iface.b.calls))
    return {
        "success": success,
        "turns": turns,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "latency_ms": latency_ms,
        "tool_calls": tool_calls,
        "wire_bytes": iface.wire_bytes,
        "cache_hits": getattr(iface, "cache_hits", 0),
        "final": final_text.strip()[:200],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--model", default="eu.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="eu-central-1")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--catalog", type=int, default=0,
                    help="Extra API surface size: MCP adds N tool schemas, REST adds N contract lines (one tool).")
    args = ap.parse_args()

    client = boto3.client("bedrock-runtime", region_name=args.region,
                          config=Config(retries={"max_attempts": 6, "mode": "adaptive"}))

    rows = []
    for trial in range(args.trials):
        for task in TASKS:
            for IF in (McpInterface, RestInterface):
                backend = Backend()
                iface = IF(backend, catalog_size=args.catalog)
                r = run_task(client, args.model, iface, task)
                r.update({"iface": iface.name, "task": task["id"], "trial": trial,
                          "catalog": args.catalog})
                rows.append(r)
                print(f"trial {trial} {iface.name:4} {task['id']:16} "
                      f"ok={int(r['success'])} turns={r['turns']} "
                      f"tok={r['total_tokens']:5} ms={r['latency_ms']:5} "
                      f"calls={r['tool_calls']} cache={r['cache_hits']}",
                      flush=True)

    with open(args.out, "w") as f:
        json.dump({"model": args.model, "region": args.region,
                   "trials": args.trials, "catalog": args.catalog, "rows": rows}, f, indent=2)
    print(f"\nwrote {args.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
