"""Scenario 2 backend: a STRICT, unfamiliar analytics API.

This is the setting where MCP's typed, injected, validated tool schemas should
earn their keep over a terse REST contract. The operations have non-obvious
names and strict parameter contracts (enums, date formats, required combos).
A REST client working from a short human contract has to GUESS the exact path,
param names and enum values; a wrong guess returns 400. MCP gives the model the
full JSON Schema up front and the host validates the call shape before dispatch,
so structurally invalid calls cannot reach the backend at all.

Same information both sides. The difference we measure is first-try correctness
on a strict surface, not tokens.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# --- the strict domain -------------------------------------------------------
# A reporting API. Metrics are enums; granularity is an enum; the date is a
# strict YYYY-MM-DD; region is a 3-letter code. Nothing here is guessable from
# a one-line description alone.

VALID_METRICS = {"gross_revenue", "net_revenue", "unit_volume", "refund_rate", "active_carts"}
VALID_GRAIN = {"hour", "day", "week"}
VALID_REGIONS = {"EUR", "NAM", "APC"}  # not "EU"/"US"/"EMEA"
DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# deterministic fact table: (metric, region, date) -> value
_FACTS = {
    ("net_revenue", "EUR", "2026-10-20"): 18422.50,
    ("gross_revenue", "EUR", "2026-10-20"): 20110.00,
    ("refund_rate", "NAM", "2026-10-20"): 0.037,
    ("unit_volume", "APC", "2026-10-19"): 1294,
    ("active_carts", "EUR", "2026-10-21"): 57,
}


@dataclass
class OpResult:
    ok: bool
    payload: dict
    status: int = 200


class StrictBackend:
    """Operation: query_metric. Strict about everything."""

    def __init__(self):
        self.calls: list[str] = []
        self.bad_calls = 0   # calls rejected as malformed/invalid

    def query_metric(self, metric=None, region=None, on_date=None, granularity="day"):
        self.calls.append("query_metric")
        errors = []
        if metric not in VALID_METRICS:
            errors.append(f"metric must be one of {sorted(VALID_METRICS)}")
        if region not in VALID_REGIONS:
            errors.append(f"region must be one of {sorted(VALID_REGIONS)}")
        if not (isinstance(on_date, str) and DATE_RX.match(on_date or "")):
            errors.append("on_date must be YYYY-MM-DD")
        if granularity not in VALID_GRAIN:
            errors.append(f"granularity must be one of {sorted(VALID_GRAIN)}")
        if errors:
            self.bad_calls += 1
            return OpResult(False, {"error": "invalid_request", "details": errors}, status=400)
        val = _FACTS.get((metric, region, on_date))
        if val is None:
            return OpResult(False, {"error": "no_data",
                                    "query": {"metric": metric, "region": region, "on_date": on_date}}, status=404)
        return OpResult(True, {"metric": metric, "region": region, "on_date": on_date,
                               "granularity": granularity, "value": val})
