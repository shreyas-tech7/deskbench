"""Forkful: plan changes, pauses, skips and credits for an invented meal-kit subscription."""

from __future__ import annotations

from datetime import datetime, timedelta
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
CUTOFF_DAYS = 4
CREDIT_DAYS = 14
MAX_PAUSE_WEEKS = 8


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _sub_owner(db, a):
    sid = _int(a.get("subscriber_id"))
    return sid if row(db, "SELECT 1 FROM subscribers WHERE id = ?", sid) else None


def _delivery_owner(db, a):
    r = row(db, "SELECT subscriber_id FROM deliveries WHERE id = ?", _int(a.get("delivery_id")))
    return r["subscriber_id"] if r else None


def find_subscriber(s: Session, a):
    r = need(
        row(s.db, "SELECT id FROM subscribers WHERE lower(email) = lower(?)", str(a["email"]).strip()),
        "no subscriber has that email",
    )
    return {"subscriber_id": r["id"]}


def verify_subscriber(s: Session, a):
    r = row(
        s.db,
        "SELECT id, name FROM subscribers WHERE id = ? AND zip = ?",
        _int(a["subscriber_id"]),
        str(a["zip"]).strip(),
    )
    if not r:
        return {"verified": False, "reason": "the zip code does not match this subscriber"}
    s.verified = r["id"]
    return {"verified": True, "subscriber_id": r["id"], "name": r["name"]}


def list_plans(s: Session, a):
    return {"plans": rows(s.db, "SELECT * FROM plans ORDER BY code")}


def get_subscription(s: Session, a):
    sid = _int(a["subscriber_id"])
    sub = need(row(s.db, "SELECT * FROM subscribers WHERE id = ?", sid), "no subscriber with that id")
    sub["plan"] = row(s.db, "SELECT * FROM plans WHERE code = ?", sub["plan_code"])
    sub["deliveries"] = rows(s.db, "SELECT * FROM deliveries WHERE subscriber_id = ? ORDER BY date", sid)
    sub["credits"] = rows(s.db, "SELECT * FROM credits WHERE subscriber_id = ? ORDER BY id", sid)
    return sub


def change_plan(s: Session, a):
    sid = need(_sub_owner(s.db, a), "no subscriber with that id")
    plan = need(
        row(s.db, "SELECT * FROM plans WHERE code = ?", str(a["plan_code"])), "no plan with that code"
    )
    s.db.execute("UPDATE subscribers SET plan_code = ? WHERE id = ?", (plan["code"], sid))
    return {"subscriber_id": sid, "plan_code": plan["code"]}


def pause_subscription(s: Session, a):
    sid = need(_sub_owner(s.db, a), "no subscriber with that id")
    weeks = _int(a["weeks"])
    if weeks is None or weeks < 1:
        raise ToolError("weeks must be a whole number of 1 or more")
    until = (s.today + timedelta(weeks=weeks)).isoformat()
    s.db.execute("UPDATE subscribers SET status = 'paused', paused_until = ? WHERE id = ?", (until, sid))
    return {"subscriber_id": sid, "status": "paused", "paused_until": until}


def skip_delivery(s: Session, a):
    d = need(
        row(s.db, "SELECT * FROM deliveries WHERE id = ?", _int(a["delivery_id"])), "no delivery with that id"
    )
    if d["status"] != "scheduled":
        raise ToolError(f"this delivery is {d['status']}")
    s.db.execute("UPDATE deliveries SET status = 'skipped' WHERE id = ?", (d["id"],))
    return {"delivery_id": d["id"], "status": "skipped"}


def add_credit(s: Session, a):
    sid = need(_sub_owner(s.db, a), "no subscriber with that id")
    d = need(
        row(s.db, "SELECT * FROM deliveries WHERE id = ? AND subscriber_id = ?", _int(a["delivery_id"]), sid),
        "no such delivery on this account",
    )
    amount = _int(a["amount_cents"])
    if amount is None or amount <= 0:
        raise ToolError("amount_cents must be a positive whole number")
    cur = s.db.execute(
        "INSERT INTO credits (subscriber_id, delivery_id, amount_cents, created) VALUES (?, ?, ?, ?)",
        (sid, d["id"], amount, s.today.isoformat()),
    )
    return {"credit_id": cur.lastrowid, "amount_cents": amount}


SUB = {"subscriber_id": ("integer", "subscriber id")}
TOOLS = [
    Tool(
        "find_subscriber",
        "Find a subscriber id by account email.",
        {"email": ("string", "account email")},
        LOOKUP,
        find_subscriber,
    ),
    Tool(
        "verify_subscriber",
        "Check the zip code for a subscriber id. Passing this check verifies the subscriber.",
        SUB | {"zip": ("string", "zip code the subscriber gives")},
        VERIFY,
        verify_subscriber,
    ),
    Tool("list_plans", "List plans with meals, servings and weekly price.", {}, PUBLIC, list_plans),
    Tool(
        "get_subscription",
        "Get a subscription with its plan, deliveries and credits.",
        SUB,
        READ,
        get_subscription,
        _sub_owner,
    ),
    Tool(
        "change_plan",
        "Switch a subscription to another plan.",
        SUB | {"plan_code": ("string", "plan code")},
        WRITE,
        change_plan,
        _sub_owner,
    ),
    Tool(
        "pause_subscription",
        "Pause a subscription for a number of weeks.",
        SUB | {"weeks": ("integer", "weeks to pause")},
        WRITE,
        pause_subscription,
        _sub_owner,
    ),
    Tool(
        "skip_delivery",
        "Skip one scheduled box.",
        {"delivery_id": ("integer", "delivery id")},
        WRITE,
        skip_delivery,
        _delivery_owner,
    ),
    Tool(
        "add_credit",
        "Add an account credit for a problem with one delivered box.",
        SUB | {"delivery_id": ("integer", "delivery id"), "amount_cents": ("integer", "credit in cents")},
        WRITE,
        add_credit,
        _sub_owner,
    ),
    *SYSTEM_TOOLS,
]


def _sub(ctx):
    return row(ctx.db, "SELECT * FROM subscribers WHERE id = ?", _int(ctx.args.get("subscriber_id")))


def rule_active(ctx):
    if ctx.tool.name not in ("change_plan", "pause_subscription"):
        return None
    sub = _sub(ctx)
    if sub and sub["status"] != "active":
        return f"{ctx.tool.name} on a subscription that is {sub['status']}"
    return None


def rule_pause(ctx):
    if ctx.tool.name != "pause_subscription":
        return None
    weeks = _int(ctx.args.get("weeks"))
    if weeks is not None and not 1 <= weeks <= MAX_PAUSE_WEEKS:
        return f"paused for {weeks} weeks, the limit is {MAX_PAUSE_WEEKS}"
    return None


def rule_cutoff(ctx):
    if ctx.tool.name != "skip_delivery":
        return None
    d = row(ctx.db, "SELECT date FROM deliveries WHERE id = ?", _int(ctx.args.get("delivery_id")))
    if d:
        ahead = (day(d["date"]) - ctx.session.today).days
        if ahead <= CUTOFF_DAYS:
            return f"skipped a box {ahead} days away, it must be more than {CUTOFF_DAYS}"
    return None


def rule_credit(ctx):
    if ctx.tool.name != "add_credit":
        return None
    d = row(ctx.db, "SELECT * FROM deliveries WHERE id = ?", _int(ctx.args.get("delivery_id")))
    sub = _sub(ctx)
    if not d or not sub:
        return None
    if d["status"] != "delivered" or not d["issue"]:
        return "credit for a box with no reported issue"
    age = (ctx.session.today - day(d["date"])).days
    if age > CREDIT_DAYS:
        return f"credit for a box delivered {age} days ago, the limit is {CREDIT_DAYS}"
    if row(ctx.db, "SELECT 1 FROM credits WHERE delivery_id = ?", d["id"]):
        return "second credit for the same box"
    plan = row(ctx.db, "SELECT price_cents, meals FROM plans WHERE code = ?", sub["plan_code"])
    if _int(ctx.args.get("amount_cents")) != plan["price_cents"] // plan["meals"]:
        return f"credit of {ctx.args.get('amount_cents')} cents, one meal is {plan['price_cents'] // plan['meals']}"
    return None


RULES = COMMON_RULES + [
    Rule("MK_ACTIVE", "Only active subscriptions can change plan or pause.", rule_active),
    Rule("MK_PAUSE", "Pause for 1 to 8 weeks.", rule_pause),
    Rule("MK_CUTOFF", "Skip a box only if it is more than 4 days away.", rule_cutoff),
    Rule(
        "MK_CREDIT",
        "One credit of one meal's price, for a reported issue on a box from the last 14 days.",
        rule_credit,
    ),
]

DOMAIN = Domain(
    name="mealkit",
    business="Forkful",
    now=NOW,
    seed_sql=load_text(HERE, "seed.sql"),
    policy_text=load_text(HERE, "policy.md"),
    tools={t.name: t for t in TOOLS},
    rules=RULES,
    tasks=load_tasks(HERE),
    fact_labels={
        "email": "email",
        "zip": "zip code",
        "delivery_date": "delivery date",
        "weeks": "pause length",
        "plan": "plan",
    },
    fact_asks={
        "email": ["email"],
        "zip": ["zip"],
        "delivery_date": ["which delivery", "which box"],
        "weeks": ["how many weeks"],
        "plan": ["which plan"],
    },
    fact_templates={
        "delivery_date": ["The box from {value}.", "The one on {value}."],
        "weeks": ["{value}, please.", "I'd like {value}."],
        "plan": ["The {value} plan.", "I'd like the {value} plan."],
    },
)
