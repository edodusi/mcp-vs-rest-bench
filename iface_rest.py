"""REST-style interface.

A REST API gives the agent ONE calling primitive (an HTTP request) plus a
contract it reads once (here: an OpenAPI-ish summary in the system prompt).
The agent constructs method + path itself. We add a real HTTP cache: the
backend returns an ETag, the agent (host) may send If-None-Match, and a
repeated unchanged read returns 304 Not Modified with an empty body. That is
the one thing MCP tool-use cannot express today, so we measure it.
"""
from __future__ import annotations
import re
from backend import Backend, OpResult

# The single tool. The model picks method + path + optional query/headers.
TOOLS = [
    {"toolSpec": {
        "name": "http_request",
        "description": (
            "Make an HTTP request to the store API. Provide method and path. "
            "Reads support ETag caching: include the header If-None-Match with a "
            "previously returned ETag to get 304 Not Modified (empty body) when "
            "the resource is unchanged."),
        "inputSchema": {"json": {"type": "object", "properties": {
            "method": {"type": "string", "enum": ["GET"]},
            "path": {"type": "string", "description": "e.g. /orders/A-100"},
            "headers": {"type": "object", "description": "Optional, e.g. {\"If-None-Match\": \"W/...\"}"},
        }, "required": ["method", "path"]}}}},
]

# Contract the model reads once, in-prompt (the REST equivalent of discovery).
CONTRACT = """\
Store REST API. Base paths:
  GET /products                      list products (optional ?category=)
  GET /products/{sku}                one product
  GET /inventory/{sku}               stock units for a SKU
  GET /orders/{order_id}             one order (status, lines, total)
  GET /customers/{customer_id}       one customer (name, tier)
  GET /customers/{customer_id}/orders  all orders for a customer
Responses are JSON. GETs return an ETag header; send If-None-Match to revalidate
and receive 304 Not Modified (empty body, meaning: reuse the value you already have).
404 means the entity does not exist."""

SYSTEM = (
    "You are an operations assistant for a small store. Call the store REST API "
    "with http_request to answer, then give a short final answer. Reuse data you "
    "already fetched; when re-reading a resource, send If-None-Match with its ETag "
    "to save bandwidth. When a 404 occurs, say the entity does not exist instead of "
    "inventing data.\n\n" + CONTRACT
)

ROUTES = [
    (re.compile(r"^/products/?$"), "list_products_q"),
    (re.compile(r"^/products/([^/]+)$"), "get_product"),
    (re.compile(r"^/inventory/([^/]+)$"), "get_inventory"),
    (re.compile(r"^/orders/([^/]+)$"), "get_order"),
    (re.compile(r"^/customers/([^/]+)/orders$"), "search_orders"),
    (re.compile(r"^/customers/([^/]+)$"), "get_customer"),
]


class RestInterface:
    name = "rest"

    def __init__(self, backend: Backend, catalog_size: int = 0):
        self.b = backend
        self.wire_bytes = 0
        self.cache_hits = 0   # 304s served
        self.gets = 0         # total GET requests
        self.catalog_size = catalog_size
        self._system = SYSTEM
        if catalog_size:
            from distractors import rest_distractor_lines
            self._system = SYSTEM + "\nAdditional endpoints:\n" + rest_distractor_lines(catalog_size)

    def tools(self):
        return TOOLS

    def system(self):
        return self._system

    def _resolve(self, path: str) -> OpResult:
        path = path.split("?")[0].rstrip("/") or "/"
        query = ""
        # recover category query for /products
        for rx, op in ROUTES:
            m = rx.match(path)
            if not m:
                continue
            if op == "list_products_q":
                return self.b.list_products(category=query or None)
            if op == "get_product":
                return self.b.get_product(sku=m.group(1))
            if op == "get_inventory":
                return self.b.get_inventory(sku=m.group(1))
            if op == "get_order":
                return self.b.get_order(order_id=m.group(1))
            if op == "search_orders":
                return self.b.search_orders(customer_id=m.group(1))
            if op == "get_customer":
                return self.b.get_customer(customer_id=m.group(1))
        return OpResult(False, {"error": "no_route", "path": path})

    def dispatch(self, tool_name: str, args: dict) -> dict:
        self.gets += 1
        raw_path = args.get("path", "")
        # parse ?category= for products
        category = None
        if "?" in raw_path and "category=" in raw_path:
            category = raw_path.split("category=")[1].split("&")[0]
        if raw_path.split("?")[0].rstrip("/") == "/products" and category:
            r = self.b.list_products(category=category)
        else:
            r = self._resolve(raw_path)

        etag = r.etag() if r.ok else None
        inm = (args.get("headers") or {}).get("If-None-Match")
        if r.ok and inm and inm == etag:
            self.cache_hits += 1
            # 304: empty body, tiny on the wire
            body = {"status": 304, "note": "Not Modified; reuse cached value"}
            self.wire_bytes += len(str(body))
            return {"ok": True, "payload": body, "_status": 304, "_etag": etag}

        status = 200 if r.ok else 404
        payload = dict(r.payload)
        if r.ok:
            payload["_etag"] = etag
        self.wire_bytes += len(r.body())
        return {"ok": r.ok, "payload": payload, "_status": status, "_etag": etag}
