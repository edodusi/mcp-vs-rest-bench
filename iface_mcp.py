"""MCP-style interface.

A stateless MCP server, over the wire, hands the model a list of tools with
JSON-Schema input definitions, and the model emits tool_use blocks the host
dispatches. Bedrock Converse's toolConfig is exactly that shape, so we model
MCP as native tool-use: rich per-tool schemas presented to the model, one
round-trip per tool call, structured tool_result back.
"""
from __future__ import annotations
from backend import Backend

# Full MCP-style tool specs: name, description, JSON schema. This is the
# discovery surface the model sees every turn (schemas are re-sent each call).
TOOLS = [
    {"toolSpec": {
        "name": "list_products",
        "description": "List catalog products, optionally filtered by category (lighting, peripherals, furniture).",
        "inputSchema": {"json": {"type": "object", "properties": {
            "category": {"type": "string", "description": "Optional category filter."}}}}}},
    {"toolSpec": {
        "name": "get_product",
        "description": "Get a single product by its SKU.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "sku": {"type": "string", "description": "Product SKU, e.g. SKU-APLE."}}, "required": ["sku"]}}}},
    {"toolSpec": {
        "name": "get_inventory",
        "description": "Get available stock units for a SKU.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "sku": {"type": "string"}}, "required": ["sku"]}}}},
    {"toolSpec": {
        "name": "get_order",
        "description": "Get an order by its order id, e.g. A-100. Returns status, lines, total.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]}}}},
    {"toolSpec": {
        "name": "get_customer",
        "description": "Get a customer record (name, tier) by customer id, e.g. cust-7.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "customer_id": {"type": "string"}}, "required": ["customer_id"]}}}},
    {"toolSpec": {
        "name": "search_orders",
        "description": "List all orders belonging to a customer id.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "customer_id": {"type": "string"}}, "required": ["customer_id"]}}}},
]

SYSTEM = (
    "You are an operations assistant for a small store. Use the available tools "
    "to answer. Call tools as needed, then give a short final answer. "
    "When a referenced entity does not exist, say so plainly instead of inventing data."
)


class McpInterface:
    """Dispatches a tool_use block against the shared backend."""
    name = "mcp"

    def __init__(self, backend: Backend, catalog_size: int = 0):
        self.b = backend
        self.wire_bytes = 0  # response body bytes returned to the model
        self.catalog_size = catalog_size
        self._tools = TOOLS
        if catalog_size:
            from distractors import mcp_distractors
            self._tools = TOOLS + mcp_distractors(catalog_size)

    def tools(self):
        return self._tools

    def system(self):
        return SYSTEM

    def dispatch(self, tool_name: str, args: dict) -> dict:
        fn = getattr(self.b, tool_name, None)
        if fn is None:
            res = {"error": "unknown_tool", "tool": tool_name}
            self.wire_bytes += len(str(res))
            return {"ok": False, "payload": res}
        r = fn(**args)
        self.wire_bytes += len(r.body())
        return {"ok": r.ok, "payload": r.payload}
