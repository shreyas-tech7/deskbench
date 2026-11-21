"""Oracle agents. Each one solves its domain by script, through the same chat and tools as any agent.

The oracle never sees a task's expected state. It reads the customer's words, asks for facts,
calls tools and applies the policy. If it passes every task, the tasks are solvable and the scorer agrees.
The flags make the broken agents that prove the scorer catches mistakes.
"""

from __future__ import annotations

import random
import re
from datetime import datetime

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


def _first(regex, text):
    m = regex.search(text)
    return m.group() if m else None


ORACLES = {"bikeparts": BikeOracle}


def oracle_for(domain_name: str, **flags) -> ScriptAgent:
    return ORACLES[domain_name](**flags)
