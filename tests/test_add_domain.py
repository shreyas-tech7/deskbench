"""The toy domain from docs/ADD_A_DOMAIN.md, built in one file. If the guide's steps drift from the code, this fails."""

import re
from datetime import datetime

from deskbench.agents.oracle import ScriptAgent
from deskbench.core import LOOKUP, SYSTEM_TOOLS, VERIFY, WRITE, Domain, Rule, Tool, need, row
from deskbench.episode import run_trial
from deskbench.policy import COMMON_RULES

SEED = """
CREATE TABLE members (id INTEGER PRIMARY KEY, card TEXT, name TEXT, birth_year TEXT);
CREATE TABLE loans (id INTEGER PRIMARY KEY, member_id INTEGER, title TEXT, renewals INTEGER);
INSERT INTO members VALUES (1, 'C-100', 'Ana Ruiz', '1990'), (2, 'C-200', 'Ben Ode', '1985');
INSERT INTO loans VALUES (10, 1, 'Moby Dick', 0), (11, 2, 'Emma', 2);
"""


def find_member(s, a):
    return {
        "member_id": need(row(s.db, "SELECT id FROM members WHERE card = ?", a["card"]), "no such card")["id"]
    }


def verify_member(s, a):
    r = row(
        s.db, "SELECT id FROM members WHERE id = ? AND birth_year = ?", a["member_id"], str(a["birth_year"])
    )
    if r:
        s.verified = r["id"]
    return {"verified": bool(r)}


def renew_loan(s, a):
    need(row(s.db, "SELECT 1 FROM loans WHERE id = ?", a["loan_id"]), "no such loan")
    s.db.execute("UPDATE loans SET renewals = renewals + 1 WHERE id = ?", (a["loan_id"],))
    return {"renewed": a["loan_id"]}


def loan_owner(db, a):
    r = row(db, "SELECT member_id FROM loans WHERE id = ?", a.get("loan_id"))
    return r["member_id"] if r else None


def rule_renew(ctx):
    if ctx.tool.name == "renew_loan":
        r = row(ctx.db, "SELECT renewals FROM loans WHERE id = ?", ctx.args.get("loan_id"))
        if r and r["renewals"] >= 2:
            return "renewed a loan that was already renewed twice"
    return None


TOOLS = [
    Tool(
        "find_member",
        "Find a member by library card.",
        {"card": ("string", "card number")},
        LOOKUP,
        find_member,
    ),
    Tool(
        "verify_member",
        "Check the birth year.",
        {"member_id": ("integer", "id"), "birth_year": ("string", "year")},
        VERIFY,
        verify_member,
    ),
    Tool("renew_loan", "Renew one loan.", {"loan_id": ("integer", "loan id")}, WRITE, renew_loan, loan_owner),
    *SYSTEM_TOOLS,
]
TASK = {
    "id": "lb01",
    "split": "dev",
    "intent": "renew",
    "tags": ["identity", "write"],
    "goal": "Ana renews Moby Dick.",
    "opening": ["I'd like to renew a book."],
    "nudge": "Can you renew it?",
    "facts": {"card": "C-100", "birth_year": "1990"},
    "expected": {
        "outcome": "resolved",
        "db": [{"table": "loans", "where": {"id": 10}, "fields": {"renewals": 1}}],
    },
}
LIBRARY = Domain(
    name="library",
    business="Paper Lantern Library",
    now=datetime(2026, 6, 15, 10, 0),
    seed_sql=SEED,
    policy_text="Renew a loan at most twice.",
    tools={t.name: t for t in TOOLS},
    rules=COMMON_RULES + [Rule("LB_RENEW", "Renew a loan at most twice.", rule_renew)],
    tasks=[TASK],
    fact_labels={"card": "card number", "birth_year": "birth year"},
    fact_asks={"card": ["card"], "birth_year": ["birth year"]},
)


class LibraryOracle(ScriptAgent):
    def script(self, opening):
        mid = yield from self.identify(
            "find_member",
            "card",
            "card number",
            re.compile(r"C-\d+"),
            "verify_member",
            "birth_year",
            "birth year",
            lambda t: (re.findall(r"\d{4}", t) or [""])[0],
            "member_id",
        )
        yield from self.confirm("I can renew Moby Dick for you.")
        yield from self.call("renew_loan", loan_id=10 if mid == 1 else 11)
        yield from self.finish("resolved", "Moby Dick is renewed.")


def test_toy_domain_oracle_passes():
    trial = run_trial(LIBRARY, TASK, LibraryOracle(), seed=1)
    assert trial["passed"], trial["problems"]


def test_toy_domain_rule_breaks_and_follows():
    from deskbench.dispatcher import Dispatcher

    disp = Dispatcher(LIBRARY, LIBRARY.fresh_db())
    disp.session.verified = 2
    disp.call("renew_loan", {"loan_id": 11}, "Yes, please.")
    assert [v["rule"] for v in disp.violations] == ["LB_RENEW"]
    disp = Dispatcher(LIBRARY, LIBRARY.fresh_db())
    disp.session.verified = 1
    disp.call("renew_loan", {"loan_id": 10}, "Yes, please.")
    assert disp.violations == []


def test_toy_domain_broken_agent_fails():
    trial = run_trial(LIBRARY, TASK, LibraryOracle(skip_identity=True), seed=1)
    assert not trial["passed"] and {v["rule"] for v in trial["violations"]} == {"IDENTITY"}
