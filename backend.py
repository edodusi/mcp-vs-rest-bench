"""Shared backend domain for the MCP-vs-REST benchmark.

One source of truth. Both the MCP interface (Bedrock tool-use) and the REST
interface (generic http_request tool) wrap THIS, so any measured difference is
the protocol/contract shape, not the business logic.

Deterministic: no randomness, same answers every run.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field


# --- seed data ---------------------------------------------------------------

PRODUCTS = {
    "SKU-APLE": {"sku": "SKU-APLE", "name": "Aurora Desk Lamp", "price_eur": 49.0, "category": "lighting"},
    "SKU-MECH": {"sku": "SKU-MECH", "name": "Mechanical Keyboard", "price_eur": 119.0, "category": "peripherals"},
    "SKU-HUBX": {"sku": "SKU-HUBX", "name": "USB-C Hub 7-in-1", "price_eur": 39.0, "category": "peripherals"},
    "SKU-CHAR": {"sku": "SKU-CHAR", "name": "Ergo Office Chair", "price_eur": 229.0, "category": "furniture"},
}

INVENTORY = {
    "SKU-APLE": 42,
    "SKU-MECH": 0,     # out of stock, used by the recovery task
    "SKU-HUBX": 300,
    "SKU-CHAR": 5,
}

ORDERS = {
    "A-100": {"order_id": "A-100", "customer": "cust-7", "status": "SHIPPED",
              "lines": [{"sku": "SKU-APLE", "qty": 2}], "total_eur": 98.0},
    "A-101": {"order_id": "A-101", "customer": "cust-7", "status": "PENDING",
              "lines": [{"sku": "SKU-MECH", "qty": 1}], "total_eur": 119.0},
    "A-102": {"order_id": "A-102", "customer": "cust-9", "status": "DELIVERED",
              "lines": [{"sku": "SKU-HUBX", "qty": 3}, {"sku": "SKU-CHAR", "qty": 1}], "total_eur": 346.0},
}

CUSTOMERS = {
    "cust-7": {"id": "cust-7", "name": "Nadia Rossi", "tier": "gold"},
    "cust-9": {"id": "cust-9", "name": "Tomas Vida", "tier": "standard"},
}


# --- operation results -------------------------------------------------------

@dataclass
class OpResult:
    ok: bool
    payload: dict
    # how many "bytes on the wire" the body would be, for a rough resource proxy
    def body(self) -> str:
        return json.dumps(self.payload, separators=(",", ":"), sort_keys=True)

    def etag(self) -> str:
        return 'W/"' + hashlib.sha256(self.body().encode()).hexdigest()[:16] + '"'


class Backend:
    """Pure domain. Operations are the SAME set the two interfaces expose."""

    def __init__(self):
        self.calls: list[str] = []  # audit of operations invoked this run

    # each method returns an OpResult; interfaces translate to tool output / HTTP

    def list_products(self, category: str | None = None) -> OpResult:
        self.calls.append("list_products")
        items = list(PRODUCTS.values())
        if category:
            items = [p for p in items if p["category"] == category]
        return OpResult(True, {"products": items})

    def get_product(self, sku: str) -> OpResult:
        self.calls.append("get_product")
        p = PRODUCTS.get(sku)
        if not p:
            return OpResult(False, {"error": "not_found", "sku": sku})
        return OpResult(True, p)

    def get_inventory(self, sku: str) -> OpResult:
        self.calls.append("get_inventory")
        if sku not in INVENTORY:
            return OpResult(False, {"error": "not_found", "sku": sku})
        return OpResult(True, {"sku": sku, "available": INVENTORY[sku]})

    def get_order(self, order_id: str) -> OpResult:
        self.calls.append("get_order")
        o = ORDERS.get(order_id)
        if not o:
            return OpResult(False, {"error": "not_found", "order_id": order_id})
        return OpResult(True, o)

    def get_customer(self, customer_id: str) -> OpResult:
        self.calls.append("get_customer")
        c = CUSTOMERS.get(customer_id)
        if not c:
            return OpResult(False, {"error": "not_found", "customer_id": customer_id})
        return OpResult(True, c)

    def search_orders(self, customer_id: str) -> OpResult:
        self.calls.append("search_orders")
        res = [o for o in ORDERS.values() if o["customer"] == customer_id]
        return OpResult(True, {"orders": res})
