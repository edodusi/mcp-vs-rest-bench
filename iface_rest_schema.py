"""REST interface with a schema-dense contract (control arm).

Same single http_request tool and same HTTP semantics as iface_rest.py, but the
in-prompt contract carries every endpoint's full JSON schema, byte-for-byte the
same name, description and inputSchema the MCP arm sends in toolConfig, plus
the method and path. This separates protocol from description format:

  - rest         terse one-line contract per endpoint
  - rest-schema  the MCP tool schemas pasted into the REST contract
  - mcp          the same schemas sent as native tools

If rest-schema input tokens land next to mcp, the token gap in the large run
comes from the density of the description, not from where it sits. Both the
system prompt and toolConfig are sent on every Converse call.
"""
from __future__ import annotations
import json
from backend import Backend
from iface_mcp import TOOLS as MCP_CORE_TOOLS
from iface_rest import RestInterface, SYSTEM as REST_SYSTEM, TOOLS

CORE_PATHS = {
    "list_products": "GET /products?category",
    "get_product": "GET /products/{sku}",
    "get_inventory": "GET /inventory/{sku}",
    "get_order": "GET /orders/{order_id}",
    "get_customer": "GET /customers/{customer_id}",
    "search_orders": "GET /customers/{customer_id}/orders",
}


def _distractor_path(name: str, props: dict) -> str:
    # Same path rule as distractors.rest_distractor_lines.
    path = "/" + name.replace("get_", "").replace("list_", "").replace("_", "-")
    if props:
        key = list(props.keys())[0]
        path += "/{" + key + "}" if name.startswith("get_") else "?" + key
    return "GET " + path


def _schema_contract(catalog_size: int) -> str:
    from distractors import mcp_distractors, _EXTRA
    entries = []
    for t in MCP_CORE_TOOLS:
        spec = t["toolSpec"]
        entries.append({"endpoint": CORE_PATHS[spec["name"]], **spec})
    for t, (name, _desc, props) in zip(mcp_distractors(catalog_size), _EXTRA[:catalog_size]):
        entries.append({"endpoint": _distractor_path(name, props), **t["toolSpec"]})
    # Compact JSON, same serialisation style as a toolConfig payload.
    return json.dumps(entries, separators=(",", ":"))


# Keep the REST system prompt wording, swap only the contract block.
_PREAMBLE = REST_SYSTEM.split("\n\n")[0]
_HTTP_NOTES = (
    "Responses are JSON. GETs return an ETag header; send If-None-Match to revalidate "
    "and receive 304 Not Modified (empty body, meaning: reuse the value you already have). "
    "404 means the entity does not exist. Path parameters in {braces}; ?name means a query parameter."
)


class RestSchemaInterface(RestInterface):
    name = "rest-schema"

    def __init__(self, backend: Backend, catalog_size: int = 0):
        super().__init__(backend, catalog_size=0)
        self.catalog_size = catalog_size
        self._system = (
            _PREAMBLE + "\n\nStore REST API. Each endpoint below is described with its "
            "JSON schema:\n" + _schema_contract(catalog_size) + "\n" + _HTTP_NOTES
        )

    def tools(self):
        return TOOLS
