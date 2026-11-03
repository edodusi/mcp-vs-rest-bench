"""Scenario 2 follow-up: how much of the schema buys first-call success?

Same strict API and same terse REST interface, with the contract enriched one
step at a time, so token cost and first-call success can be read as a curve:

  rest              terse contract (names the params only)
  rest-enums        + the allowed values for metric, region and granularity
  rest-enums-date   + the date format (YYYY-MM-DD)
  rest-schema       + the MCP arm's full JSON schema for query_metric

Suggested in the dev.to comments on the MCP vs REST post.
"""
from __future__ import annotations
import json
from strict_backend import VALID_METRICS, VALID_GRAIN, VALID_REGIONS
from strict_scenario import StrictRest, REST_SYSTEM, REST_CONTRACT, MCP_TOOLS

_ENUMS = (
    "\n  Allowed values:"
    f"\n    metric: {', '.join(sorted(VALID_METRICS))}"
    f"\n    region: {', '.join(sorted(VALID_REGIONS))}"
    f"\n    granularity: {', '.join(sorted(VALID_GRAIN))}"
)
_DATE = "\n    on_date: YYYY-MM-DD"
_SCHEMA = ("\n  Body JSON schema: "
           + json.dumps(MCP_TOOLS[0]["toolSpec"]["inputSchema"]["json"], separators=(",", ":")))


def _system(extra: str) -> str:
    return REST_SYSTEM.replace(REST_CONTRACT, REST_CONTRACT + extra)


class StrictRestEnums(StrictRest):
    name = "rest-enums"

    def system(self):
        return _system(_ENUMS)


class StrictRestEnumsDate(StrictRest):
    name = "rest-enums-date"

    def system(self):
        return _system(_ENUMS + _DATE)


class StrictRestSchema(StrictRest):
    name = "rest-schema"

    def system(self):
        return _system(_SCHEMA)
