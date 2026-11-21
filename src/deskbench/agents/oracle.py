"""Oracle agents. Each one solves its domain by script, through the same chat and tools as any agent.

The oracle never sees a task's expected state. It reads the customer's words, asks for facts,
calls tools and applies the policy. If it passes every task, the tasks are solvable and the scorer agrees.
The flags make the broken agents that prove the scorer catches mistakes.
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

from ..episode import Call, Say

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ZIP = re.compile(r"\b\d{5}\b")
ORDER_NO = re.compile(r"\b1\d{3}\b")
PHONE = re.compile(r"\b\d{3}-\d{4}\b")
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
TIME = re.compile(r"\b\d\d:\d\d\b")
INT = re.compile(r"\b\d+\b")


def classify(text: str, intents: list[tuple[str, list[str]]]) -> str:
    low = text.lower()
    return next((name for name, words in intents if any(w in low for w in words)), "unknown")


def pick(names, text: str):
    """The longest name that appears in the text, so 'Race saddle' beats 'saddle'."""
    low = text.lower()
    hits = [n for n in names if n.lower() in low]
    return max(hits, key=len) if hits else None


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


class ScriptAgent:
    name = "oracle"
    INTENTS: list[tuple[str, list[str]]] = []

    def __init__(self, skip_identity=False, ignore_windows=False, skip_confirm=0.0, name=None):
        self.skip_identity, self.ignore_windows, self.skip_confirm = (
            skip_identity,
            ignore_windows,
            skip_confirm,
        )
        if name:
            self.name = name

    def reset(self, domain, seed):
        self.domain, self.gen, self.tokens = domain, None, 0
        self.rng = random.Random(f"agent:{seed}")

    @property
    def now(self) -> datetime:
        return self.domain.now

    def act(self, obs):
        try:
            if self.gen is None:
                self.gen = self.script(obs[1])
                return next(self.gen)
            return self.gen.send(obs[1] if obs[0] == "user" else obs[2])
        except StopIteration:
            return Say("Thanks for contacting us.")

    # Small generator helpers. `reply = yield from self.say(...)` waits for the user's answer.
    def say(self, text):
        return (yield Say(text))

    def call(self, name, **args):
        return (yield Call(name, args))

    def confirm(self, text):
        if self.skip_confirm and self.rng.random() < self.skip_confirm:
            return
        yield Say(text + " Shall I go ahead?")

    def finish(self, resolution, text):
        yield Say(text + " Is there anything else I can help with?")
        yield Call("close_ticket", {"resolution": resolution, "note": text[:120]})

    def refuse(self, text):
        yield from self.finish("refused", "I'm sorry, but " + text)

    def transfer(self, reason):
        yield Call("transfer_to_human", {"reason": reason})

    def in_window(self, ok: bool) -> bool:
        return True if self.ignore_windows else ok

    def identify(
        self, find, find_arg, find_label, find_re, verify, check_arg, check_label, check_re, id_field
    ):
        """Look the customer up, then verify. Returns the id, or None if the check fails twice."""
        reply = yield from self.say(f"I can help with that. First, what is the {find_label} on your account?")
        res = yield from self.call(find, **{find_arg: _first(find_re, reply) or ""})
        if "error" in res:
            return None
        cid = res[id_field]
        if self.skip_identity:
            return cid
        for attempt in range(2):
            ask = f"Thanks. What is the {check_label} on the account?"
            if attempt:
                ask = f"That {check_label} does not match. Could you check your {check_label} once more?"
            reply = yield from self.say(ask)
            res = yield from self.call(verify, **{id_field: cid, check_arg: check_re(reply) or ""})
            if res.get("verified"):
                return cid
        return None


class BikeOracle(ScriptAgent):
    INTENTS = [
        ("damaged", ["damaged", "missing package"]),
        ("exchange", ["exchange", "swap"]),
        ("cancel", ["cancel"]),
        ("return", ["return", "send back"]),
        ("question", ["question", "in stock"]),
    ]

    def script(self, opening):
        intent = classify(opening, self.INTENTS)
        if intent == "damaged":
            yield from self.transfer("item arrived damaged")
            return
        if intent == "question":
            reply = yield from self.say("Happy to help. Which product are you asking about?")
            catalog = (yield from self.call("search_products", query=""))["products"]
            p = next((p for p in catalog if p["name"] == pick([c["name"] for c in catalog], reply)), None)
            if p is None:
                yield from self.finish("resolved", "I could not find that product.")
                return
            yield from self.finish(
                "resolved",
                f"The {p['name']} costs {money(p['price_cents'])} and we have {p['stock']} in stock.",
            )
            return
        cid = yield from self.identify(
            "find_customer",
            "email",
            "email",
            EMAIL,
            "verify_customer",
            "zip",
            "zip code",
            lambda r: _first(ZIP, r),
            "customer_id",
        )
        if cid is None:
            yield from self.refuse("I could not verify your account, so I cannot make changes to it.")
            return
        need_item = intent in ("return", "exchange")
        reply = yield from self.say(
            "What is the order number" + (", and which item is this about?" if need_item else "?")
        )
        order, item = None, None
        m = ORDER_NO.search(reply)
        if m:
            order = yield from self.call("get_order", order_id=int(m.group()))
        elif need_item:
            for o in (yield from self.call("list_orders", customer_id=cid))["orders"]:
                if pick([i["name"] for i in o["items"]], reply):
                    order = o
        if not order or "error" in order:
            yield from self.refuse("I could not find that order on your account.")
            return
        if need_item:
            name = pick([i["name"] for i in order["items"]], reply)
            item = next((i for i in order["items"] if i["name"] == name), None)
            if item is None:
                yield from self.refuse("I could not find that item in the order.")
                return
        if intent == "cancel":
            yield from self.cancel(order)
        elif intent == "return":
            yield from self.return_(order, item)
        else:
            yield from self.exchange(order, item)

    def cancel(self, order):
        if order["status"] != "processing":
            yield from self.refuse(
                f"order {order['id']} is already {order['status']}, so I cannot cancel it. You can return it once it arrives."
            )
            return
        yield from self.confirm(f"I can cancel order {order['id']}.")
        yield from self.call("cancel_order", order_id=order["id"])
        yield from self.finish("resolved", f"Order {order['id']} is cancelled.")

    def returnable(self, order, item):
        if item["final_sale"]:
            return f"the {item['name']} was a final-sale item, so it cannot be returned or exchanged."
        if order["status"] != "delivered" and not self.ignore_windows:
            return f"order {order['id']} has not been delivered yet."
        if order["delivered_date"]:
            age = (self.now.date() - datetime.fromisoformat(order["delivered_date"]).date()).days
            if not self.in_window(age <= 30):
                return f"returns and exchanges are only possible within 30 days of delivery, and this order arrived {age} days ago."
        return None

    def return_(self, order, item):
        why = self.returnable(order, item)
        if why:
            yield from self.refuse(why)
            return
        qty = item["qty"] - item["returned_qty"] - item["exchanged_qty"]
        if qty > 1:
            m = INT.search(
                (yield from self.say(f"You have {qty} of those. How many would you like to return?"))
            )
            qty = min(qty, int(m.group())) if m else qty
        refund = qty * item["price_cents"]
        yield from self.confirm(
            f"I can return {qty} x {item['name']} from order {order['id']} for a refund of {money(refund)} to your original payment."
        )
        yield from self.call("return_item", order_id=order["id"], sku=item["sku"], qty=qty)
        yield from self.finish("resolved", f"Your refund of {money(refund)} is on its way.")

    def exchange(self, order, item):
        why = self.returnable(order, item)
        if why:
            yield from self.refuse(why)
            return
        reply = yield from self.say("What would you like instead?")
        catalog = (yield from self.call("search_products", query=""))["products"]
        new = next((p for p in catalog if p["name"] == pick([c["name"] for c in catalog], reply)), None)
        if new is None:
            yield from self.refuse("I could not find that product.")
            return
        if new["category"] != item["category"] or new["price_cents"] != item["price_cents"]:
            yield from self.refuse("an exchange needs an item in the same category with the same price.")
            return
        if new["stock"] < 1:
            yield from self.refuse(f"the {new['name']} is out of stock, so I cannot exchange it right now.")
            return
        yield from self.confirm(
            f"I can exchange your {item['name']} from order {order['id']} for a {new['name']}."
        )
        yield from self.call("exchange_item", order_id=order["id"], sku=item["sku"], new_sku=new["sku"])
        yield from self.finish("resolved", f"Your {new['name']} will ship within 2 days.")


def _last_name(text):
    words = [
        w for w in re.findall(r"\b[A-Z][a-z]+\b", text) if w not in ("My", "It", "Sure", "Sorry", "Thanks")
    ]
    return words[-1] if words else None


class SalonOracle(ScriptAgent):
    INTENTS = [
        ("complaint", ["complaint", "not happy", "unhappy"]),
        ("reschedule", ["reschedule", "move"]),
        ("cancel", ["cancel"]),
        ("book", ["book"]),
        ("question", ["how much", "price", "cost"]),
    ]

    def script(self, opening):
        intent = classify(opening, self.INTENTS)
        if intent == "complaint":
            yield from self.transfer("complaint about a past service")
            return
        services = (yield from self.call("list_services"))["services"]
        if intent == "question":
            reply = yield from self.say("Happy to help. Which service are you asking about?")
            sv = next((v for v in services if v["name"] == pick([v["name"] for v in services], reply)), None)
            if sv is None:
                yield from self.finish("resolved", "I could not find that service.")
                return
            dep = (
                f" and needs a {money(sv['deposit_cents'])} deposit"
                if sv["deposit_cents"]
                else " with no deposit"
            )
            yield from self.finish("resolved", f"A {sv['name']} costs {money(sv['price_cents'])}{dep}.")
            return
        cid = yield from self.identify(
            "find_client",
            "phone",
            "phone number",
            PHONE,
            "verify_client",
            "last_name",
            "last name",
            _last_name,
            "client_id",
        )
        if cid is None:
            yield from self.refuse("I could not verify your details, so I cannot make changes.")
            return
        bookings = (yield from self.call("list_bookings", client_id=cid))["bookings"]
        if intent == "book":
            yield from self.book(cid, bookings, services)
            return
        verb = "cancel" if intent == "cancel" else "move"
        reply = yield from self.say(f"Which appointment would you like to {verb}? Please tell me the date.")
        d = _first(DATE, reply)
        b = next((b for b in bookings if b["status"] == "booked" and b["start"][:10] == d), None)
        if b is None:
            yield from self.refuse("I could not find an upcoming appointment on that date.")
            return
        hours = (datetime.fromisoformat(b["start"]) - self.now).total_seconds() / 3600
        if intent == "cancel":
            yield from self.cancel(b, hours)
        else:
            yield from self.reschedule(b, hours)

    def cancel(self, b, hours):
        refund = b["deposit_status"] == "held" and self.in_window(hours >= 24)
        note = ""
        if b["deposit_status"] == "held":
            note = (
                f" Your {money(b['deposit_cents'])} deposit will be refunded."
                if refund
                else f" The {money(b['deposit_cents'])} deposit is not refundable, because the appointment is less than 24 hours away."
            )
        yield from self.confirm(f"I can cancel your {b['service']} on {b['start']}.{note}")
        yield from self.call("cancel_booking", booking_id=b["id"], refund_deposit=refund)
        yield from self.finish("resolved", f"Your {b['service']} on {b['start']} is cancelled.")

    def reschedule(self, b, hours):
        if b["reschedules"] >= 1:
            yield from self.refuse("an appointment can be moved only once, and this one was already moved.")
            return
        if not self.in_window(hours >= 24):
            yield from self.refuse("appointments can only be moved 24 hours or more ahead.")
            return
        reply = yield from self.say("What date and time would you like?")
        new = f"{_first(DATE, reply)} {_first(TIME, reply)}"
        slots = yield from self.call("find_open_slots", service_code=b["service_code"], date=new[:10])
        if not any(x["stylist_id"] == b["stylist_id"] and x["start"] == new for x in slots.get("slots", [])):
            yield from self.refuse(f"{b['stylist']} is not free at {new}.")
            return
        yield from self.confirm(f"I can move your {b['service']} with {b['stylist']} to {new}.")
        yield from self.call("reschedule_booking", booking_id=b["id"], new_start=new)
        yield from self.finish("resolved", f"Your appointment is now on {new}.")

    def book(self, cid, bookings, services):
        since = self.now - timedelta(days=90)
        missed = sum(
            1 for b in bookings if b["status"] == "no_show" and datetime.fromisoformat(b["start"]) >= since
        )
        if missed >= 2:
            yield from self.transfer("client has two or more missed appointments in 90 days")
            return
        reply = yield from self.say(
            "Which service would you like, which stylist would you prefer, and what date and time work for you?"
        )
        sv = next((v for v in services if v["name"] == pick([v["name"] for v in services], reply)), None)
        when = f"{_first(DATE, reply)} {_first(TIME, reply)}"
        if sv is None or "None" in when:
            yield from self.refuse("I could not work out the service or the time.")
            return
        slots = (yield from self.call("find_open_slots", service_code=sv["code"], date=when[:10])).get(
            "slots", []
        )
        name = pick({x["stylist"] for x in slots}, reply)
        slot = next((x for x in slots if x["stylist"] == name and x["start"] == when), None)
        if slot is None:
            yield from self.refuse(f"that time is not free with {name or 'that stylist'}.")
            return
        if sv["needs_senior"] and slot["level"] != "senior":
            yield from self.refuse(f"a {sv['name']} needs a senior stylist, and {name} is a junior stylist.")
            return
        dep = f" A {money(sv['deposit_cents'])} deposit will be held." if sv["deposit_cents"] else ""
        yield from self.confirm(f"I can book a {sv['name']} with {name} on {when}.{dep}")
        yield from self.call(
            "book_appointment",
            client_id=cid,
            stylist_id=slot["stylist_id"],
            service_code=sv["code"],
            start=when,
        )
        yield from self.finish("resolved", f"You are booked for {when} with {name}.")


class MealkitOracle(ScriptAgent):
    INTENTS = [
        ("cancel", ["cancel"]),
        ("credit", ["credit", "problem"]),
        ("skip", ["skip"]),
        ("pause", ["pause"]),
        ("plan", ["switch", "change my plan"]),
        ("question", ["how much", "price", "cost"]),
    ]

    def script(self, opening):
        intent = classify(opening, self.INTENTS)
        if intent == "cancel":
            yield from self.transfer("cancellation request for the retention team")
            return
        plans = (yield from self.call("list_plans"))["plans"]
        if intent == "question":
            reply = yield from self.say("Happy to help. Which plan are you asking about?")
            p = next((p for p in plans if p["name"] == pick([p["name"] for p in plans], reply)), None)
            if p is None:
                yield from self.finish("resolved", "I could not find that plan.")
                return
            yield from self.finish(
                "resolved",
                f"The {p['name']} plan costs {money(p['price_cents'])} a week, which is {money(p['price_cents'] // p['meals'])} per meal.",
            )
            return
        sid = yield from self.identify(
            "find_subscriber",
            "email",
            "email",
            EMAIL,
            "verify_subscriber",
            "zip",
            "zip code",
            lambda r: _first(ZIP, r),
            "subscriber_id",
        )
        if sid is None:
            yield from self.refuse("I could not verify your account, so I cannot make changes to it.")
            return
        if intent == "unknown":
            yield from self.transfer("could not tell what the subscriber needs")
            return
        sub = yield from self.call("get_subscription", subscriber_id=sid)
        yield from getattr(self, intent)(sub, plans)

    def _delivery(self, sub, reply):
        d = _first(DATE, reply)
        return next((x for x in sub["deliveries"] if x["date"] == d), None)

    def credit(self, sub, plans):
        reply = yield from self.say("Which delivery had the problem? Please tell me the date.")
        d = self._delivery(sub, reply)
        if d is None or d["status"] != "delivered" or not d["issue"]:
            yield from self.refuse(
                "credits are only for a delivered box with an issue you reported in the app."
            )
            return
        age = (self.now.date() - datetime.fromisoformat(d["date"]).date()).days
        if not self.in_window(age <= 14):
            yield from self.refuse(
                f"credits are only for boxes from the last 14 days, and this one arrived {age} days ago."
            )
            return
        if any(c["delivery_id"] == d["id"] for c in sub["credits"]):
            yield from self.refuse("this box already received a credit.")
            return
        amount = sub["plan"]["price_cents"] // sub["plan"]["meals"]
        yield from self.confirm(
            f"I can add a credit of {money(amount)}, the price of one meal, for the box from {d['date']}."
        )
        yield from self.call("add_credit", subscriber_id=sub["id"], delivery_id=d["id"], amount_cents=amount)
        yield from self.finish("resolved", f"A {money(amount)} credit is on your account.")

    def skip(self, sub, plans):
        reply = yield from self.say("Which delivery would you like to skip? Please tell me the date.")
        d = self._delivery(sub, reply)
        if d is None or d["status"] != "scheduled":
            yield from self.refuse("I could not find a scheduled box on that date.")
            return
        ahead = (datetime.fromisoformat(d["date"]).date() - self.now.date()).days
        if not self.in_window(ahead > 4):
            yield from self.refuse(
                f"the box on {d['date']} is already being packed, so it can no longer be skipped."
            )
            return
        yield from self.confirm(f"I can skip your box on {d['date']}.")
        yield from self.call("skip_delivery", delivery_id=d["id"])
        yield from self.finish("resolved", f"Your box on {d['date']} is skipped.")

    def pause(self, sub, plans):
        if sub["status"] != "active":
            yield from self.refuse(f"your subscription is {sub['status']}, so it cannot be paused again.")
            return
        m = INT.search((yield from self.say("How many weeks would you like to pause?")))
        weeks = int(m.group()) if m else 0
        if not 1 <= weeks <= 8:
            yield from self.refuse("a pause can be 1 to 8 weeks long.")
            return
        until = (self.now.date() + timedelta(weeks=weeks)).isoformat()
        yield from self.confirm(f"I can pause your subscription for {weeks} weeks, until {until}.")
        yield from self.call("pause_subscription", subscriber_id=sub["id"], weeks=weeks)
        yield from self.finish("resolved", f"Your subscription is paused until {until}.")

    def plan(self, sub, plans):
        if sub["status"] != "active":
            yield from self.refuse(
                f"your subscription is {sub['status']}, and only active subscriptions can change plan."
            )
            return
        reply = yield from self.say("Which plan would you like to switch to?")
        p = next((p for p in plans if p["name"] == pick([p["name"] for p in plans], reply)), None)
        if p is None:
            yield from self.refuse("I could not find that plan.")
            return
        yield from self.confirm(
            f"I can switch you to the {p['name']} plan at {money(p['price_cents'])} a week."
        )
        yield from self.call("change_plan", subscriber_id=sub["id"], plan_code=p["code"])
        yield from self.finish("resolved", f"You are now on the {p['name']} plan.")


def _first(regex, text):
    m = regex.search(text)
    return m.group() if m else None


ORACLES = {"bikeparts": BikeOracle, "salon": SalonOracle, "mealkit": MealkitOracle}


def oracle_for(domain_name: str, **flags) -> ScriptAgent:
    return ORACLES[domain_name](**flags)
