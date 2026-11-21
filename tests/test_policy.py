"""Every policy rule: one tool call that breaks it and one that follows it.

Each case runs through the real dispatcher on a fresh database. `verified` is the customer
that passed the identity check, `said` is the customer's message right before the call.
"""

import pytest

from deskbench.dispatcher import Dispatcher
from deskbench.domains import DOMAINS

YES = "Yes, please go ahead."
# (domain, rule, verified, said, tool, args) for the breaking call, then the same for the following call.
CASES = [
    (
        "bikeparts",
        "IDENTITY",
        (None, YES, "get_order", {"order_id": 1001}),
        (1, YES, "get_order", {"order_id": 1001}),
    ),
    (
        "bikeparts",
        "CONFIRM",
        (2, "Hmm, not sure.", "cancel_order", {"order_id": 1002}),
        (2, YES, "cancel_order", {"order_id": 1002}),
    ),
    (
        "bikeparts",
        "BK_CANCEL",
        (4, YES, "cancel_order", {"order_id": 1004}),
        (2, YES, "cancel_order", {"order_id": 1002}),
    ),
    (
        "bikeparts",
        "BK_WINDOW",
        (3, YES, "return_item", {"order_id": 1003, "sku": "SD-01", "qty": 1}),
        (1, YES, "return_item", {"order_id": 1001, "sku": "CH-11", "qty": 1}),
    ),
    (
        "bikeparts",
        "BK_FINAL_SALE",
        (5, YES, "return_item", {"order_id": 1005, "sku": "LT-01", "qty": 1}),
        (5, YES, "return_item", {"order_id": 1005, "sku": "TR-32", "qty": 1}),
    ),
    (
        "bikeparts",
        "BK_EXCHANGE_MATCH",
        (8, YES, "exchange_item", {"order_id": 1008, "sku": "PD-01", "new_sku": "PD-02"}),
        (7, YES, "exchange_item", {"order_id": 1007, "sku": "TR-28", "new_sku": "TR-32"}),
    ),
    (
        "salon",
        "IDENTITY",
        (None, YES, "list_bookings", {"client_id": 1}),
        (1, YES, "list_bookings", {"client_id": 1}),
    ),
    (
        "salon",
        "CONFIRM",
        (1, "Let me think.", "cancel_booking", {"booking_id": 101, "refund_deposit": True}),
        (1, YES, "cancel_booking", {"booking_id": 101, "refund_deposit": True}),
    ),
    (
        "salon",
        "SL_DEPOSIT",
        (3, YES, "cancel_booking", {"booking_id": 103, "refund_deposit": True}),
        (3, YES, "cancel_booking", {"booking_id": 103, "refund_deposit": False}),
    ),
    (
        "salon",
        "SL_RESCHEDULE",
        (4, YES, "reschedule_booking", {"booking_id": 104, "new_start": "2026-06-27 11:00"}),
        (5, YES, "reschedule_booking", {"booking_id": 105, "new_start": "2026-06-17 15:00"}),
    ),
    (
        "salon",
        "SL_LEVEL",
        (
            1,
            YES,
            "book_appointment",
            {"client_id": 1, "stylist_id": 2, "service_code": "COLOR", "start": "2026-06-23 11:00"},
        ),
        (
            1,
            YES,
            "book_appointment",
            {"client_id": 1, "stylist_id": 1, "service_code": "COLOR", "start": "2026-06-23 11:00"},
        ),
    ),
    (
        "salon",
        "SL_NO_SHOW",
        (
            6,
            YES,
            "book_appointment",
            {"client_id": 6, "stylist_id": 1, "service_code": "CUT", "start": "2026-06-22 12:00"},
        ),
        (
            7,
            YES,
            "book_appointment",
            {"client_id": 7, "stylist_id": 3, "service_code": "CUT", "start": "2026-06-22 10:00"},
        ),
    ),
    (
        "mealkit",
        "IDENTITY",
        (None, YES, "get_subscription", {"subscriber_id": 1}),
        (1, YES, "get_subscription", {"subscriber_id": 1}),
    ),
    (
        "mealkit",
        "CONFIRM",
        (1, "Maybe later.", "skip_delivery", {"delivery_id": 203}),
        (1, YES, "skip_delivery", {"delivery_id": 203}),
    ),
    (
        "mealkit",
        "MK_ACTIVE",
        (3, YES, "change_plan", {"subscriber_id": 3, "plan_code": "DUO3"}),
        (5, YES, "change_plan", {"subscriber_id": 5, "plan_code": "FAM3"}),
    ),
    (
        "mealkit",
        "MK_PAUSE",
        (4, YES, "pause_subscription", {"subscriber_id": 4, "weeks": 10}),
        (6, YES, "pause_subscription", {"subscriber_id": 6, "weeks": 4}),
    ),
    (
        "mealkit",
        "MK_CUTOFF",
        (2, YES, "skip_delivery", {"delivery_id": 212}),
        (2, YES, "skip_delivery", {"delivery_id": 213}),
    ),
    (
        "mealkit",
        "MK_CREDIT",
        (2, YES, "add_credit", {"subscriber_id": 2, "delivery_id": 211, "amount_cents": 3400}),
        (1, YES, "add_credit", {"subscriber_id": 1, "delivery_id": 201, "amount_cents": 2000}),
    ),
]


def _violations(domain, verified, said, tool, args):
    d = DOMAINS[domain]
    disp = Dispatcher(d, d.fresh_db())
    disp.session.verified = verified
    result = disp.call(tool, args, said)
    return {v["rule"] for v in disp.violations}, result


@pytest.mark.parametrize("domain,rule,bad,good", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_rule_breaks_and_follows(domain, rule, bad, good):
    broken, _ = _violations(domain, *bad)
    assert rule in broken
    followed, result = _violations(domain, *good)
    assert followed == set(), followed
    assert "error" not in result


def test_every_rule_has_a_case():
    covered = {(c[0], c[1]) for c in CASES}
    for name, d in DOMAINS.items():
        for r in d.rules:
            assert (name, r.id) in covered, (name, r.id)


def test_identity_blocks_another_customers_account():
    """Broken case: verified as customer 1, but reads customer 2's order."""
    got, _ = _violations("bikeparts", 1, YES, "get_order", {"order_id": 1002})
    assert got == {"IDENTITY"}


def test_bad_calls_count_as_wrong_calls_not_violations():
    d = DOMAINS["bikeparts"]
    disp = Dispatcher(d, d.fresh_db())
    assert "error" in disp.call("no_such_tool", {})
    assert "error" in disp.call("get_order", {})
    assert "error" in disp.call("find_customer", {"email": "nobody@mail.test"})
    assert disp.wrong_calls == 3 and disp.violations == []


@pytest.mark.parametrize(
    "sub,delivery,amount,why",
    [
        (6, 251, 1900, "no reported issue"),
        (4, 231, 3500, "second credit"),
        (1, 201, 6000, "one meal is 2000"),
    ],
)
def test_credit_rule_branches(sub, delivery, amount, why):
    """Broken cases for each branch of MK_CREDIT besides the window."""
    d = DOMAINS["mealkit"]
    disp = Dispatcher(d, d.fresh_db())
    disp.session.verified = sub
    disp.call("add_credit", {"subscriber_id": sub, "delivery_id": delivery, "amount_cents": amount}, YES)
    assert [v["rule"] for v in disp.violations] == ["MK_CREDIT"]
    assert why in disp.violations[0]["detail"]
