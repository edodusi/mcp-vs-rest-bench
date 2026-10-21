"""Scenario 2 interfaces: strict analytics API, MCP vs terse REST.

MCP: one tool, query_metric, with a FULL JSON Schema. Enums are enumerated,
the date format is stated, every param typed. The host validates the toolUse
input against the schema and rejects a malformed call before dispatch, exactly
as an MCP host does.

REST: one http_request tool plus a TERSE contract, the kind a human actually
writes: it names the endpoint and the params but does NOT spell out every valid
enum value or the exact date format. The model must infer them. This is the
realistic REST discovery surface; pasting the full JSON Schema for every
endpoint into the prompt is exactly the token cost that lost in scenario 1.
"""
from __future__ import annotations
import json
from strict_backend import StrictBackend, VALID_METRICS, VALID_GRAIN, VALID_REGIONS

# ---- MCP: full typed schema -------------------------------------------------
MCP_TOOLS = [
    {"toolSpec": {
        "name": "query_metric",
        "description": "Query one analytics metric for a region on a date.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": sorted(VALID_METRICS),
                           "description": "Which metric to return."},
                "region": {"type": "string", "enum": sorted(VALID_REGIONS),
                           "description": "Region code."},
                "on_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$",
                            "description": "Date in YYYY-MM-DD."},
                "granularity": {"type": "string", "enum": sorted(VALID_GRAIN),
                                "description": "Time grain. Default day."},
            },
            "required": ["metric", "region", "on_date"],
        }}}},
]

MCP_SYSTEM = (
    "You are an analytics assistant. Use the query_metric tool to answer, then "
    "give a short final answer with the number. If the backend returns no_data, "
    "say there is no data for that query instead of inventing a number."
)

# ---- REST: terse contract (must infer the strict bits) ----------------------
REST_TOOLS = [
    {"toolSpec": {
        "name": "http_request",
        "description": "Call the analytics API. Provide method, path and an optional JSON body.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "method": {"type": "string"},
            "path": {"type": "string"},
            "body": {"type": "object"},
        }, "required": ["method", "path"]}}}},
]

# Deliberately terse: names the op and params, not the enums or the date format.
REST_CONTRACT = """\
Analytics API.
  POST /metrics/query   body: { metric, region, on_date, granularity? }
                        Returns the metric value. Returns 400 on an invalid
                        request, 404 when there is no data for the query."""

REST_SYSTEM = (
    "You are an analytics assistant. Call the analytics API with http_request "
    "to answer, then give a short final answer with the number. If you get a 400, "
    "read the error details and correct the request. If you get 404 no_data, say "
    "there is no data instead of inventing a number.\n\n" + REST_CONTRACT
)


class StrictMcp:
    name = "mcp"

    def __init__(self, backend: StrictBackend):
        self.b = backend
        self.wire_bytes = 0
        self.cache_hits = 0
        self.schema_rejections = 0  # calls the host rejected before dispatch

    def tools(self):
        return MCP_TOOLS

    def system(self):
        return MCP_SYSTEM

    def _validate(self, args: dict):
        """Host-side JSON-Schema validation, as an MCP host does."""
        errs = []
        for req in ("metric", "region", "on_date"):
            if req not in args:
                errs.append(f"missing required field {req}")
        if "metric" in args and args["metric"] not in VALID_METRICS:
            errs.append("metric not in enum")
        if "region" in args and args["region"] not in VALID_REGIONS:
            errs.append("region not in enum")
        if "granularity" in args and args["granularity"] not in VALID_GRAIN:
            errs.append("granularity not in enum")
        return errs

    def dispatch(self, tool_name, args):
        errs = self._validate(args)
        if errs:
            # host rejects malformed input before it reaches the backend
            self.schema_rejections += 1
            body = {"error": "schema_validation_failed", "details": errs}
            self.wire_bytes += len(json.dumps(body))
            return {"ok": False, "payload": body}
        r = self.b.query_metric(**{k: args[k] for k in
                                   ("metric", "region", "on_date", "granularity") if k in args})
        self.wire_bytes += len(json.dumps(r.payload))
        return {"ok": r.ok, "payload": r.payload}


class StrictRest:
    name = "rest"

    def __init__(self, backend: StrictBackend):
        self.b = backend
        self.wire_bytes = 0
        self.cache_hits = 0
        self.schema_rejections = 0  # not used; REST has no host-side schema

    def tools(self):
        return REST_TOOLS

    def system(self):
        return REST_SYSTEM

    def dispatch(self, tool_name, args):
        path = (args.get("path") or "").split("?")[0].rstrip("/")
        body = args.get("body") or {}
        if path != "/metrics/query" or (args.get("method") or "").upper() != "POST":
            # strict router: wrong path/method is a 404, no fuzzy matching
            self.b.bad_calls += 1
            out = {"error": "not_found", "note": "no such endpoint", "path": args.get("path")}
            self.wire_bytes += len(json.dumps(out))
            return {"ok": False, "payload": out}
        r = self.b.query_metric(
            metric=body.get("metric"), region=body.get("region"),
            on_date=body.get("on_date"), granularity=body.get("granularity", "day"))
        self.wire_bytes += len(json.dumps(r.payload))
        return {"ok": r.ok, "payload": r.payload}


# ---- strict task suite ------------------------------------------------------
# Prompts use NATURAL language (region words, loose metric names) so the model
# must map to the strict enum values. This is where typed discovery helps.

def _num(text, *cands):
    t = text.replace(",", "")
    return any(c in t for c in cands)

STRICT_TASKS = [
    {"id": "net_rev_eur",
     "prompt": "What was net revenue in Europe on 2026-10-20?",
     "grade": lambda t, b: _num(t, "18422", "18,422", "18422.5")},
    {"id": "gross_rev_eur",
     "prompt": "Give me gross revenue for the European region on October 20, 2026.",
     "grade": lambda t, b: _num(t, "20110", "20,110")},
    {"id": "refund_nam",
     "prompt": "What was the refund rate in North America on 2026-10-20?",
     "grade": lambda t, b: ("3.7" in t or "0.037" in t)},
    {"id": "units_apc",
     "prompt": "How many units were sold in the Asia-Pacific region on 2026-10-19?",
     "grade": lambda t, b: _num(t, "1294", "1,294")},
    {"id": "carts_eur",
     "prompt": "How many active carts in Europe on 2026-10-21?",
     "grade": lambda t, b: "57" in t},
]
