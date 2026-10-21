"""Scenario 2 runner: strict API, measure first-try correctness.

Metrics per run:
  success            grader passed (right number in final answer)
  turns              agent<->tool round-trips
  tool_calls         number of tool_use blocks
  bad_calls          backend 400s (invalid request reached backend) +
                     MCP host schema rejections  -> total malformed attempts
  first_call_ok      the agent's FIRST tool call succeeded (status 200)
  total_tokens       summed
  latency_ms

Run: python strict_runner.py --trials 6
"""
from __future__ import annotations
import argparse, json, time, statistics
import boto3
from botocore.config import Config

from strict_backend import StrictBackend
from strict_scenario import StrictMcp, StrictRest, STRICT_TASKS

MAX_TURNS = 8


def run_task(client, model, iface, task):
    messages = [{"role": "user", "content": [{"text": task["prompt"]}]}]
    in_tok = out_tok = turns = tool_calls = 0
    first_call_ok = None
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
        in_tok += u["inputTokens"]; out_tok += u["outputTokens"]
        out_msg = resp["output"]["message"]
        messages.append(out_msg)
        if resp["stopReason"] == "tool_use":
            results = []
            for block in out_msg["content"]:
                if "toolUse" not in block:
                    continue
                tu = block["toolUse"]; tool_calls += 1
                res = iface.dispatch(tu["name"], tu.get("input") or {})
                if first_call_ok is None:
                    first_call_ok = bool(res["ok"])
                results.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"json": res["payload"]}],
                    "status": "success" if res["ok"] else "error"}})
            messages.append({"role": "user", "content": results})
            continue
        for block in out_msg["content"]:
            if "text" in block:
                final_text += block["text"] + " "
        break

    # total malformed attempts: backend 400s + MCP host schema rejections
    bad = iface.b.bad_calls + getattr(iface, "schema_rejections", 0)
    return {
        "success": bool(task["grade"](final_text, iface.b)),
        "turns": turns, "tool_calls": tool_calls,
        "bad_calls": bad,
        "first_call_ok": bool(first_call_ok),
        "total_tokens": in_tok + out_tok,
        "latency_ms": int((time.time() - t0) * 1000),
        "final": final_text.strip()[:200],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--model", default="eu.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="eu-central-1")
    ap.add_argument("--out", default="results-strict.json")
    args = ap.parse_args()
    client = boto3.client("bedrock-runtime", region_name=args.region,
                          config=Config(retries={"max_attempts": 6, "mode": "adaptive"}))
    rows = []
    for trial in range(args.trials):
        for task in STRICT_TASKS:
            for IF in (StrictMcp, StrictRest):
                iface = IF(StrictBackend())
                r = run_task(client, args.model, iface, task)
                r.update({"iface": iface.name, "task": task["id"], "trial": trial})
                rows.append(r)
                print(f"trial {trial} {iface.name:4} {task['id']:14} ok={int(r['success'])} "
                      f"first_ok={int(r['first_call_ok'])} bad={r['bad_calls']} "
                      f"calls={r['tool_calls']} tok={r['total_tokens']:5}", flush=True)
    json.dump({"model": args.model, "trials": args.trials, "rows": rows},
              open(args.out, "w"), indent=2)
    print(f"\nwrote {args.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
