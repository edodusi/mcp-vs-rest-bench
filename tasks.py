"""Task suite. Same tasks for both interfaces.

Each task: a prompt and a grader(final_text, backend_calls) -> bool.
Graders are substring/któ-style checks on the final answer plus, where it
matters, on which backend operations actually ran.
"""
from __future__ import annotations
import re


def _has(text, *needles):
    t = text.lower()
    return all(n.lower() in t for n in needles)


TASKS = [
    # 1. simple lookup
    {"id": "order_status",
     "prompt": "What is the status of order A-100?",
     "grade": lambda t, calls: _has(t, "shipped")},

    # 2. two-hop: order -> customer name
    {"id": "order_customer",
     "prompt": "Who is the customer on order A-101? Give their name.",
     "grade": lambda t, calls: _has(t, "nadia")},

    # 3. aggregate across a customer's orders
    {"id": "customer_total",
     "prompt": "List all order ids for customer cust-7.",
     "grade": lambda t, calls: _has(t, "a-100") and _has(t, "a-101")},

    # 4. missing-info recovery: nonexistent order
    {"id": "missing_order",
     "prompt": "What is the status of order A-999?",
     "grade": lambda t, calls: (("not" in t.lower() and ("exist" in t.lower() or "found" in t.lower()))
                                or "no such" in t.lower())},

    # 5. conditional: stock check drives the answer (SKU-MECH is 0)
    {"id": "stock_mech",
     "prompt": "Can I order 1 unit of the Mechanical Keyboard right now? Answer yes or no and why.",
     "grade": lambda t, calls: ("no" in t.lower()) and ("0" in t or "out of stock" in t.lower() or "no stock" in t.lower())},

    # 6. repeated read -> caching opportunity (read order A-102 twice, then confirm total)
    {"id": "repeat_read",
     "prompt": ("Read order A-102 and tell me its total. Then, to be safe, verify the "
                "total by reading order A-102 once more and confirm it is unchanged."),
     "grade": lambda t, calls: "346" in t},
]
