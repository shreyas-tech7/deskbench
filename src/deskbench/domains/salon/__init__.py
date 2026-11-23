"""Clip & Curl: bookings, cancellations and deposits for an invented hair salon."""

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
from ...policy import COMMON_RULES, moment

HERE = Path(__file__).parent
NOW = datetime(2026, 6, 15, 10, 0)
HOURS = range(9, 17)


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _truthy(v) -> bool:
    return v is True or str(v).strip().lower() in ("true", "1", "yes")


def _start(text) -> str:
    """Normalize '2026-06-17 15:00' or '2026-06-17T15:00'. Raises ToolError on anything else."""
    try:
        t = datetime.fromisoformat(str(text).strip().replace("T", " "))
    except ValueError:
        raise ToolError("start must look like 2026-06-17 15:00") from None
    if t.minute or t.hour not in HOURS:
        raise ToolError("appointments start on the hour between 09:00 and 16:00")
    return t.strftime("%Y-%m-%d %H:%M")


def _hours_ahead(now: datetime, start: str) -> float:
    return (moment(start) - now).total_seconds() / 3600


def _booking_owner(db, a):
    r = row(db, "SELECT client_id FROM bookings WHERE id = ?", _int(a.get("booking_id")))
    return r["client_id"] if r else None


def _client_owner(db, a):
    cid = _int(a.get("client_id"))
    return cid if row(db, "SELECT 1 FROM clients WHERE id = ?", cid) else None


def _busy(db, stylist_id, start, skip_id=None) -> bool:
    return bool(
        row(
            db,
            "SELECT 1 FROM bookings WHERE stylist_id = ? AND start = ? AND status = 'booked' AND id IS NOT ?",
            stylist_id,
            start,
            skip_id,
        )
    )


def find_client(s: Session, a):
    r = need(
        row(s.db, "SELECT id FROM clients WHERE phone = ?", str(a["phone"]).strip()),
        "no client has that phone number",
    )
    return {"client_id": r["id"]}


def verify_client(s: Session, a):
    r = row(s.db, "SELECT id, name FROM clients WHERE id = ?", _int(a["client_id"]))
    last = str(a["last_name"]).strip().lower()
    if not r or not last or r["name"].lower().split()[-1] != last:
        return {"verified": False, "reason": "the last name does not match this client"}
    s.verified = r["id"]
    return {"verified": True, "client_id": r["id"], "name": r["name"]}


def list_services(s: Session, a):
    out = rows(s.db, "SELECT * FROM services ORDER BY code")
    for x in out:
        x["needs_senior"] = bool(x["needs_senior"])
    return {"services": out}


def find_open_slots(s: Session, a):
    need(
        row(s.db, "SELECT 1 FROM services WHERE code = ?", str(a["service_code"])),
        "no service with that code",
    )
    try:
        day = datetime.fromisoformat(str(a["date"])[:10]).date()
    except ValueError:
        raise ToolError("date must look like 2026-06-17") from None
    out = []
    for st in rows(s.db, "SELECT * FROM stylists ORDER BY id"):
        for h in HOURS:
            start = f"{day.isoformat()} {h:02d}:00"
            if moment(start) > s.now and not _busy(s.db, st["id"], start):
                out.append(
                    {"stylist_id": st["id"], "stylist": st["name"], "level": st["level"], "start": start}
                )
    return {"slots": out}


def list_bookings(s: Session, a):
    return {
        "bookings": rows(
            s.db,
            "SELECT b.*, v.name AS service, st.name AS stylist FROM bookings b JOIN services v ON v.code = b.service_code "
            "JOIN stylists st ON st.id = b.stylist_id WHERE b.client_id = ? ORDER BY b.start",
            _int(a["client_id"]),
        )
    }


def book_appointment(s: Session, a):
    cid = need(_client_owner(s.db, a), "no client with that id")
    st = need(
        row(s.db, "SELECT * FROM stylists WHERE id = ?", _int(a["stylist_id"])), "no stylist with that id"
    )
    sv = need(
        row(s.db, "SELECT * FROM services WHERE code = ?", str(a["service_code"])),
        "no service with that code",
    )
    start = _start(a["start"])
    if moment(start) <= s.now:
        raise ToolError("that time has passed")
    if _busy(s.db, st["id"], start):
        raise ToolError("that stylist is busy at that time")
    held = "held" if sv["deposit_cents"] else "none"
    cur = s.db.execute(
        "INSERT INTO bookings (client_id, stylist_id, service_code, start, status, deposit_cents, deposit_status) "
        "VALUES (?, ?, ?, ?, 'booked', ?, ?)",
        (cid, st["id"], sv["code"], start, sv["deposit_cents"], held),
    )
    return {"booking_id": cur.lastrowid, "start": start, "deposit_cents": sv["deposit_cents"]}


def _upcoming(s: Session, a) -> dict:
    b = need(
        row(s.db, "SELECT * FROM bookings WHERE id = ?", _int(a["booking_id"])), "no booking with that id"
    )
    if b["status"] != "booked":
        raise ToolError(f"this booking is {b['status']}")
    return b


def cancel_booking(s: Session, a):
    b = _upcoming(s, a)
    dep = b["deposit_status"]
    if dep == "held":
        dep = "refunded" if _truthy(a["refund_deposit"]) else "forfeited"
    s.db.execute("UPDATE bookings SET status = 'cancelled', deposit_status = ? WHERE id = ?", (dep, b["id"]))
    return {"booking_id": b["id"], "status": "cancelled", "deposit": dep}


def reschedule_booking(s: Session, a):
    b = _upcoming(s, a)
    start = _start(a["new_start"])
    if moment(start) <= s.now:
        raise ToolError("that time has passed")
    if _busy(s.db, b["stylist_id"], start, b["id"]):
        raise ToolError("the stylist is busy at that time")
    s.db.execute(
        "UPDATE bookings SET start = ?, reschedules = reschedules + 1 WHERE id = ?", (start, b["id"])
    )
    return {"booking_id": b["id"], "start": start}


BOOKING = {"booking_id": ("integer", "booking id")}
TOOLS = [
    Tool(
        "find_client",
        "Find a client id by phone number.",
        {"phone": ("string", "phone number, like 555-0101")},
        LOOKUP,
        find_client,
    ),
    Tool(
        "verify_client",
        "Check the last name for a client id. Passing this check verifies the client.",
        {
            "client_id": ("integer", "id from find_client"),
            "last_name": ("string", "last name the client gives"),
        },
        VERIFY,
        verify_client,
    ),
    Tool(
        "list_services",
        "List services with price, deposit and whether they need a senior stylist.",
        {},
        PUBLIC,
        list_services,
    ),
    Tool(
        "find_open_slots",
        "List free start times on a date for every stylist, with the stylist's level.",
        {"service_code": ("string", "service code"), "date": ("string", "date, like 2026-06-17")},
        PUBLIC,
        find_open_slots,
    ),
    Tool(
        "list_bookings",
        "List a client's bookings, past and upcoming.",
        {"client_id": ("integer", "client id")},
        READ,
        list_bookings,
        _client_owner,
    ),
    Tool(
        "book_appointment",
        "Book an appointment. Holds the service's deposit.",
        {
            "client_id": ("integer", "client id"),
            "stylist_id": ("integer", "stylist id"),
            "service_code": ("string", "service code"),
            "start": ("string", "start time, like 2026-06-17 15:00"),
        },
        WRITE,
        book_appointment,
        _client_owner,
    ),
    Tool(
        "cancel_booking",
        "Cancel a booking. If a deposit is held, refund it or keep it.",
        BOOKING | {"refund_deposit": ("boolean", "true to refund a held deposit, false to keep it")},
        WRITE,
        cancel_booking,
        _booking_owner,
    ),
    Tool(
        "reschedule_booking",
        "Move a booking to a new start time with the same stylist.",
        BOOKING | {"new_start": ("string", "new start time, like 2026-06-17 15:00")},
        WRITE,
        reschedule_booking,
        _booking_owner,
    ),
    *SYSTEM_TOOLS,
]


def _booking(ctx):
    return row(ctx.db, "SELECT * FROM bookings WHERE id = ?", _int(ctx.args.get("booking_id")))


def rule_deposit(ctx):
    if ctx.tool.name != "cancel_booking":
        return None
    b = _booking(ctx)
    if not b or b["deposit_status"] != "held":
        return None
    due = _hours_ahead(ctx.session.now, b["start"]) >= 24
    if _truthy(ctx.args.get("refund_deposit")) != due:
        return f"refund_deposit was {ctx.args.get('refund_deposit')!r} but the deposit {'is' if due else 'is not'} refundable"
    return None


def rule_reschedule(ctx):
    if ctx.tool.name != "reschedule_booking":
        return None
    b = _booking(ctx)
    if not b:
        return None
    if b["reschedules"] >= 1:
        return "moved an appointment that was already moved once"
    hours = _hours_ahead(ctx.session.now, b["start"])
    if hours < 24:
        return f"moved an appointment {hours:.0f} hours ahead, the limit is 24"
    return None


def rule_level(ctx):
    if ctx.tool.name != "book_appointment":
        return None
    sv = row(ctx.db, "SELECT needs_senior FROM services WHERE code = ?", str(ctx.args.get("service_code")))
    st = row(ctx.db, "SELECT level FROM stylists WHERE id = ?", _int(ctx.args.get("stylist_id")))
    if sv and st and sv["needs_senior"] and st["level"] != "senior":
        return "booked a senior-only service with a junior stylist"
    return None


def rule_no_show(ctx):
    if ctx.tool.name != "book_appointment":
        return None
    since = (ctx.session.now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M")
    n = row(
        ctx.db,
        "SELECT count(*) AS n FROM bookings WHERE client_id = ? AND status = 'no_show' AND start >= ?",
        _int(ctx.args.get("client_id")),
        since,
    )["n"]
    if n >= 2:
        return f"booked a client with {n} missed appointments in 90 days"
    return None


RULES = COMMON_RULES + [
    Rule(
        "SL_DEPOSIT",
        "Refund a held deposit if the appointment is 24 hours away or more, and keep it otherwise.",
        rule_deposit,
    ),
    Rule(
        "SL_RESCHEDULE", "Move an appointment once at most, and only 24 hours ahead or more.", rule_reschedule
    ),
    Rule("SL_LEVEL", "Full color and Balayage need a senior stylist.", rule_level),
    Rule("SL_NO_SHOW", "No chat bookings for clients with two or more no-shows in 90 days.", rule_no_show),
]

DOMAIN = Domain(
    name="salon",
    business="Clip & Curl",
    now=NOW,
    seed_sql=load_text(HERE, "seed.sql"),
    policy_text=load_text(HERE, "policy.md"),
    tools={t.name: t for t in TOOLS},
    rules=RULES,
    tasks=load_tasks(HERE),
    fact_labels={
        "phone": "phone number",
        "last_name": "last name",
        "appointment_date": "appointment date",
        "new_time": "time",
        "service": "service",
        "stylist": "stylist",
    },
    fact_asks={
        "phone": ["phone"],
        "last_name": ["last name"],
        "appointment_date": ["which appointment"],
        "new_time": ["what date and time"],
        "service": ["which service"],
        "stylist": ["which stylist"],
    },
    fact_templates={
        "appointment_date": ["The one on {value}.", "It's the appointment on {value}."],
        "new_time": ["{value} works for me.", "How about {value}?"],
        "service": ["{value}, please.", "I'd like {value}."],
        "stylist": ["{value}, if possible.", "I'd like {value}."],
    },
)
