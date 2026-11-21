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
]


def _violations(domain, verified, said, tool, args):
    d = DOMAINS[domain]
    disp = Dispatcher(d, d.fresh_db())
    disp.session.verified = verified
    result = disp.call(tool, args, said)
    return {v["rule"] for v in disp.violations}, result


@pytest.mark.parametrize("domain,rule,bad,good", CASES, ids=[c[1] for c in CASES])
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
