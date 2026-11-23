"""The scorer reads only state: named fields, row counts, other changes, the ticket and the policy log."""

from deskbench.domains import DOMAINS
from deskbench.scorer import check_db, score, snapshot

D = DOMAINS["bikeparts"]
TASK = D.task("bk03")  # cancel order 1002


def _run(sql_list, outcome=None):
    db = D.fresh_db()
    before = snapshot(db)
    for sql in sql_list:
        db.execute(sql)
    if outcome:
        db.execute("UPDATE ticket SET status = ? WHERE id = 1", (outcome,))
    return before, db


def test_correct_state_passes():
    before, db = _run(["UPDATE orders SET status = 'cancelled' WHERE id = 1002"], "resolved")
    assert score(TASK, before, db, [])["passed"]


def test_wrong_field_fails():
    """Broken case: the order is still processing."""
    before, db = _run([], "resolved")
    r = score(TASK, before, db, [])
    assert not r["passed"] and any("status" in p for p in r["problems"])


def test_extra_change_fails():
    """Broken case: the right cancel plus a stray cancel of another order."""
    before, db = _run(
        [
            "UPDATE orders SET status = 'cancelled' WHERE id = 1002",
            "UPDATE orders SET status = 'cancelled' WHERE id = 1009",
        ],
        "resolved",
    )
    r = score(TASK, before, db, [])
    assert not r["passed"] and any("unexpected change" in p for p in r["problems"])


def test_wrong_outcome_fails():
    """Broken case: the right database but the chat was transferred."""
    before, db = _run(["UPDATE orders SET status = 'cancelled' WHERE id = 1002"], "transferred")
    assert not score(TASK, before, db, [])["passed"]


def test_open_ticket_fails():
    before, db = _run(["UPDATE orders SET status = 'cancelled' WHERE id = 1002"])
    assert score(TASK, before, db, [])["outcome"] == "open"
    assert not score(TASK, before, db, [])["passed"]


def test_policy_violation_fails():
    """Broken case: right state, but a rule fired on the way."""
    before, db = _run(["UPDATE orders SET status = 'cancelled' WHERE id = 1002"], "resolved")
    r = score(TASK, before, db, [{"rule": "CONFIRM", "detail": "no yes"}])
    assert not r["passed"] and r["problems"] == ["policy CONFIRM: no yes"]


def test_count_spec_and_new_rows():
    db = D.fresh_db()
    before = snapshot(db)
    spec = [{"table": "returns", "where": {"order_id": 1003}, "count": 0}]
    assert check_db(before, snapshot(db), spec) == []
    db.execute(
        "INSERT INTO returns (order_id, sku, qty, refund_cents, created) VALUES (1003, 'SD-01', 1, 5999, 'x')"
    )
    assert check_db(before, snapshot(db), spec) == ["returns {'order_id': 1003}: expected 0 rows, found 1"]


def test_deleted_row_is_a_change():
    before, db = _run(["DELETE FROM customers WHERE id = 8"], "resolved")
    assert any("unexpected change in customers" in p for p in check_db(before, snapshot(db), []))


def test_extra_column_change_on_a_named_row_fails():
    """Found in review: switching Tess's plan and also pausing her passed, because the row was covered."""
    from deskbench.domains import DOMAINS
    from deskbench.scorer import score, snapshot

    d = DOMAINS["mealkit"]
    db = d.fresh_db()
    before = snapshot(db)
    db.execute(
        "UPDATE subscribers SET plan_code = 'FAM3', status = 'paused', paused_until = '2026-07-13' WHERE id = 5"
    )
    db.execute("UPDATE ticket SET status = 'resolved'")
    res = score(d.task("mk10"), before, db, [])
    assert not res["passed"] and any("status" in p for p in res["problems"])
