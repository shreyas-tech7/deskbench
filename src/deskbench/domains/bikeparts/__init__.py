"""Spoke & Sprocket: orders, returns and exchanges for an invented online bike-parts store."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ...core import (
    LOOKUP,
    PUBLIC,
    READ,
    SYSTEM_TOOLS,
    VERIFY,
    WRITE,
    Domain,
    Rule,
    Session,
    Tool,
    ToolError,
    load_tasks,
    load_text,
    need,
    row,
    rows,
)
from ...policy import COMMON_RULES, day

HERE = Path(__file__).parent
NOW = datetime(2026, 6, 15, 10, 0)
WINDOW_DAYS = 30


def _order_owner(db, a):
    r = row(db, "SELECT customer_id FROM orders WHERE id = ?", _int(a.get("order_id")))
    return r["customer_id"] if r else None


def _int(v):
    try:
        return int(str(v).lstrip("#"))
    except ValueError:
        return None


def _item(db, a, sku_key="sku"):
    return row(
        db,
        "SELECT i.*, p.name, p.category, p.final_sale FROM order_items i JOIN products p USING (sku) "
        "WHERE i.order_id = ? AND i.sku = ?",
        _int(a.get("order_id")),
        str(a.get(sku_key, "")),
    )


def find_customer(s: Session, a):
    r = need(
        row(s.db, "SELECT id FROM customers WHERE lower(email) = lower(?)", str(a["email"]).strip()),
        "no customer has that email",
    )
    return {"customer_id": r["id"]}


def verify_customer(s: Session, a):
    r = row(
        s.db,
        "SELECT id, name FROM customers WHERE id = ? AND zip = ?",
        _int(a["customer_id"]),
        str(a["zip"]).strip(),
    )
    if not r:  # a failed check is an answer, not a wrong call
        return {"verified": False, "reason": "the zip code does not match this customer"}
    s.verified = r["id"]
    return {"verified": True, "customer_id": r["id"], "name": r["name"]}


def search_products(s: Session, a):
    words = str(a["query"]).lower().split()
    out = []
    for p in rows(s.db, "SELECT * FROM products ORDER BY sku"):
        if all(w in p["name"].lower() for w in words):
            p["final_sale"] = bool(p["final_sale"])
            out.append(p)
    return {"products": out}


def _order(db, order_id):
    o = need(row(db, "SELECT * FROM orders WHERE id = ?", order_id), "no order with that number")
    o["items"] = rows(
        db,
        "SELECT i.sku, p.name, p.category, i.qty, i.price_cents, i.returned_qty, i.exchanged_qty, p.final_sale "
        "FROM order_items i JOIN products p USING (sku) WHERE i.order_id = ? ORDER BY i.sku",
        order_id,
    )
    for i in o["items"]:
        i["final_sale"] = bool(i["final_sale"])
    return o


def get_order(s: Session, a):
    return _order(s.db, _int(a["order_id"]))


def list_orders(s: Session, a):
    ids = [
        r["id"]
        for r in rows(s.db, "SELECT id FROM orders WHERE customer_id = ? ORDER BY id", _int(a["customer_id"]))
    ]
    return {"orders": [_order(s.db, i) for i in ids]}


def cancel_order(s: Session, a):
    o = _order(s.db, _int(a["order_id"]))
    if o["status"] == "cancelled":
        raise ToolError("order is already cancelled")
    s.db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (o["id"],))
    return {"order_id": o["id"], "status": "cancelled"}


def return_item(s: Session, a):
    it = need(_item(s.db, a), "that item is not in this order")
    qty = _int(a["qty"])
    left = it["qty"] - it["returned_qty"] - it["exchanged_qty"]
    if qty is None or not 1 <= qty <= left:
        raise ToolError(f"quantity must be between 1 and {left}")
    refund = qty * it["price_cents"]
    s.db.execute(
        "UPDATE order_items SET returned_qty = returned_qty + ? WHERE order_id = ? AND sku = ?",
        (qty, it["order_id"], it["sku"]),
    )
    s.db.execute(
        "INSERT INTO returns (order_id, sku, qty, refund_cents, created) VALUES (?, ?, ?, ?, ?)",
        (it["order_id"], it["sku"], qty, refund, s.today.isoformat()),
    )
    return {"returned": qty, "sku": it["sku"], "refund_cents": refund, "refund_to": "original payment"}


def exchange_item(s: Session, a):
    it = need(_item(s.db, a), "that item is not in this order")
    new = need(
        row(s.db, "SELECT * FROM products WHERE sku = ?", str(a["new_sku"])), "no product with that sku"
    )
    if it["qty"] - it["returned_qty"] - it["exchanged_qty"] < 1:
        raise ToolError("nothing left to exchange on this line")
    if new["stock"] < 1:
        raise ToolError("the new item is out of stock")
    s.db.execute(
        "UPDATE order_items SET exchanged_qty = exchanged_qty + 1 WHERE order_id = ? AND sku = ?",
        (it["order_id"], it["sku"]),
    )
    s.db.execute("UPDATE products SET stock = stock - 1 WHERE sku = ?", (new["sku"],))
    s.db.execute(
        "INSERT INTO exchanges (order_id, old_sku, new_sku, created) VALUES (?, ?, ?, ?)",
        (it["order_id"], it["sku"], new["sku"], s.today.isoformat()),
    )
    return {"exchanged": it["sku"], "for": new["sku"], "ships": "within 2 days"}


ORDER = {"order_id": ("integer", "order number")}
TOOLS = [
    Tool(
        "find_customer",
        "Find a customer id by the email on the account.",
        {"email": ("string", "account email")},
        LOOKUP,
        find_customer,
    ),
    Tool(
        "verify_customer",
        "Check the zip code for a customer id. Passing this check verifies the customer.",
        {
            "customer_id": ("integer", "id from find_customer"),
            "zip": ("string", "zip code the customer gives"),
        },
        VERIFY,
        verify_customer,
    ),
    Tool(
        "search_products",
        "Search products by words in the name.",
        {"query": ("string", "words to search")},
        PUBLIC,
        search_products,
    ),
    Tool(
        "list_orders",
        "List a customer's orders with their items.",
        {"customer_id": ("integer", "customer id")},
        READ,
        list_orders,
        lambda db, a: (
            _int(a.get("customer_id"))
            if row(db, "SELECT 1 FROM customers WHERE id = ?", _int(a.get("customer_id")))
            else None
        ),
    ),
    Tool(
        "get_order", "Get one order with its items, status and dates.", ORDER, READ, get_order, _order_owner
    ),
    Tool("cancel_order", "Cancel an order.", ORDER, WRITE, cancel_order, _order_owner),
    Tool(
        "return_item",
        "Return items from an order and refund them to the original payment.",
        ORDER | {"sku": ("string", "sku of the item"), "qty": ("integer", "how many to return")},
        WRITE,
        return_item,
        _order_owner,
    ),
    Tool(
        "exchange_item",
        "Exchange one unit of an item for another product.",
        ORDER
        | {
            "sku": ("string", "sku of the item to send back"),
            "new_sku": ("string", "sku of the replacement"),
        },
        WRITE,
        exchange_item,
        _order_owner,
    ),
    *SYSTEM_TOOLS,
]


def rule_cancel(ctx):
    if ctx.tool.name != "cancel_order":
        return None
    o = row(ctx.db, "SELECT status FROM orders WHERE id = ?", _int(ctx.args.get("order_id")))
    if o and o["status"] != "processing":
        return f"cancelled an order whose status is {o['status']}"
    return None


def rule_window(ctx):
    if ctx.tool.name not in ("return_item", "exchange_item"):
        return None
    o = row(ctx.db, "SELECT status, delivered_date FROM orders WHERE id = ?", _int(ctx.args.get("order_id")))
    if not o:
        return None
    if o["status"] != "delivered":
        return f"{ctx.tool.name} on an order that is {o['status']}"
    age = (ctx.session.today - day(o["delivered_date"])).days
    if age > WINDOW_DAYS:
        return f"{ctx.tool.name} {age} days after delivery, the window is {WINDOW_DAYS}"
    return None


def rule_final_sale(ctx):
    if ctx.tool.name not in ("return_item", "exchange_item"):
        return None
    it = _item(ctx.db, ctx.args)
    if it and it["final_sale"]:
        return f"{ctx.tool.name} on final-sale item {it['sku']}"
    return None


def rule_exchange_match(ctx):
    if ctx.tool.name != "exchange_item":
        return None
    old = row(ctx.db, "SELECT category, price_cents FROM products WHERE sku = ?", str(ctx.args.get("sku")))
    new = row(
        ctx.db, "SELECT category, price_cents FROM products WHERE sku = ?", str(ctx.args.get("new_sku"))
    )
    if old and new and (old["category"], old["price_cents"]) != (new["category"], new["price_cents"]):
        return "exchange to an item with a different category or price"
    return None


RULES = COMMON_RULES + [
    Rule("BK_CANCEL", "Cancel only orders that are still processing.", rule_cancel),
    Rule("BK_WINDOW", "Return or exchange only delivered orders, within 30 days of delivery.", rule_window),
    Rule("BK_FINAL_SALE", "Final-sale items cannot be returned or exchanged.", rule_final_sale),
    Rule("BK_EXCHANGE_MATCH", "An exchange needs the same category and the same price.", rule_exchange_match),
]

DOMAIN = Domain(
    name="bikeparts",
    business="Spoke & Sprocket",
    now=NOW,
    seed_sql=load_text(HERE, "seed.sql"),
    policy_text=load_text(HERE, "policy.md"),
    tools={t.name: t for t in TOOLS},
    rules=RULES,
    tasks=load_tasks(HERE),
    fact_labels={
        "email": "email",
        "zip": "zip code",
        "order_id": "order number",
        "item": "item",
        "quantity": "quantity",
        "new_item": "replacement",
    },
    fact_asks={
        "email": ["email"],
        "zip": ["zip"],
        "order_id": ["order number"],
        "item": ["which item", "which product"],
        "quantity": ["how many"],
        "new_item": ["instead"],
    },
    fact_templates={
        "item": ["It's the {value}.", "The {value}."],
        "quantity": ["{value}, please.", "I'd like to return {value}."],
        "new_item": ["The {value}, please.", "I'd like the {value}."],
    },
)
