"""Distractor tools to model API surface size.

The core of the "MCP token tax" debate: a stateless MCP server re-sends every
tool's schema on every turn, so cost scales with the SIZE of the API surface,
whether or not the agent uses those tools. A REST contract is read once and the
agent keeps using one http_request primitive no matter how big the API is.

We model a realistically large store API (many endpoints the task does not need)
by padding:
  - MCP: add N extra tool specs (full schemas) to the tool list.
  - REST: add the same N endpoints as lines in the in-prompt contract (text),
          still ONE http_request tool.

Same information, different placement: MCP pays per-turn, REST pays once.
"""
from __future__ import annotations
import copy

_EXTRA = [
    ("list_categories", "List all product categories.", {}),
    ("get_category", "Get a category by id.", {"category_id": "string"}),
    ("list_customers", "List all customers.", {}),
    ("search_products", "Full-text search products by keyword.", {"q": "string"}),
    ("get_shipment", "Get a shipment by id.", {"shipment_id": "string"}),
    ("track_shipment", "Get tracking events for a shipment.", {"shipment_id": "string"}),
    ("get_invoice", "Get an invoice by id.", {"invoice_id": "string"}),
    ("list_invoices", "List invoices for a customer.", {"customer_id": "string"}),
    ("get_refund", "Get a refund by id.", {"refund_id": "string"}),
    ("list_refunds", "List refunds for an order.", {"order_id": "string"}),
    ("get_warehouse", "Get a warehouse by code.", {"code": "string"}),
    ("list_warehouses", "List all warehouses.", {}),
    ("get_supplier", "Get a supplier by id.", {"supplier_id": "string"}),
    ("list_suppliers", "List suppliers for a SKU.", {"sku": "string"}),
    ("get_promotion", "Get an active promotion by code.", {"code": "string"}),
    ("list_promotions", "List active promotions.", {}),
    ("get_review", "Get a product review by id.", {"review_id": "string"}),
    ("list_reviews", "List reviews for a SKU.", {"sku": "string"}),
    ("get_address", "Get a customer address by id.", {"address_id": "string"}),
    ("list_addresses", "List addresses for a customer.", {"customer_id": "string"}),
    ("get_cart", "Get a cart by id.", {"cart_id": "string"}),
    ("get_wishlist", "Get a wishlist by id.", {"wishlist_id": "string"}),
    ("get_loyalty", "Get loyalty balance for a customer.", {"customer_id": "string"}),
    ("list_tickets", "List support tickets for a customer.", {"customer_id": "string"}),
]


def mcp_distractors(n: int):
    out = []
    for name, desc, props in _EXTRA[:n]:
        schema = {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}}
        if props:
            schema["required"] = list(props.keys())
        out.append({"toolSpec": {"name": name, "description": desc, "inputSchema": {"json": schema}}})
    return out


def rest_distractor_lines(n: int):
    lines = []
    for name, desc, props in _EXTRA[:n]:
        path = "/" + name.replace("get_", "").replace("list_", "").replace("_", "-")
        if props:
            path += "/{" + list(props.keys())[0] + "}" if name.startswith("get_") else "?" + list(props.keys())[0]
        lines.append(f"  GET {path:38} {desc}")
    return "\n".join(lines)
