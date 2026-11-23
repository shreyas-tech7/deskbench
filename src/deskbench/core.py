"""Shared building blocks: tools, policy rules, domains and the per-trial session."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

TICKET_SQL = """
CREATE TABLE ticket (id INTEGER PRIMARY KEY, status TEXT NOT NULL, note TEXT);
INSERT INTO ticket VALUES (1, 'open', NULL);
"""
# Tool kinds. "read" and "write" touch one customer's account, so the identity rule covers them.
PUBLIC, LOOKUP, VERIFY, READ, WRITE, SYSTEM = "public", "lookup", "verify", "read", "write", "system"


class ToolError(Exception):
    """A tool refused the call because the data is wrong (unknown id, bad argument)."""


@dataclass
class Session:
    db: sqlite3.Connection
    now: datetime
    verified: int | None = None  # customer id that passed the identity check
    ended: str | None = None  # resolved, refused or transferred once the ticket closes

    @property
    def today(self) -> date:
        return self.now.date()


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    params: dict[str, tuple[str, str]]  # name -> (json type, description)
    kind: str
    fn: Callable[[Session, dict], Any]
    owner: Callable[[sqlite3.Connection, dict], int | None] | None = None  # customer the call touches

    def schema(self) -> dict:
        """OpenAI tool format."""
        props = {k: {"type": t, "description": d} for k, (t, d) in self.params.items()}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": list(self.params)},
            },
        }


@dataclass(frozen=True)
class CallCtx:
    tool: Tool
    args: dict
    session: Session
    last_user: str  # the user's message right before this call

    @property
    def db(self) -> sqlite3.Connection:
        return self.session.db


@dataclass(frozen=True)
class Rule:
    id: str
    text: str
    check: Callable[[CallCtx], str | None]  # returns a violation message or None


@dataclass
class Domain:
    name: str
    business: str
    now: datetime
    seed_sql: str
    policy_text: str
    tools: dict[str, Tool]
    rules: list[Rule]
    tasks: list[dict]
    fact_labels: dict[str, str]  # fact key -> how the user names it
    fact_asks: dict[str, list[str]]  # fact key -> phrases that ask for it
    fact_templates: dict[str, list[str]] = field(default_factory=dict)  # optional wording per fact

    def fresh_db(self) -> sqlite3.Connection:
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript(self.seed_sql + TICKET_SQL)
        return db

    def task(self, task_id: str) -> dict:
        return next(t for t in self.tasks if t["id"] == task_id)


def load_text(here: Path, name: str) -> str:
    return (here / name).read_text(encoding="utf-8")


def load_tasks(here: Path) -> list[dict]:
    return json.loads((here / "tasks.json").read_text(encoding="utf-8"))


def row(db: sqlite3.Connection, sql: str, *args) -> dict | None:
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def rows(db: sqlite3.Connection, sql: str, *args) -> list[dict]:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def need(value, message: str):
    if value is None:
        raise ToolError(message)
    return value


def close_ticket(s: Session, a: dict):
    res = a.get("resolution")
    if res not in ("resolved", "refused"):
        raise ToolError("resolution must be 'resolved' or 'refused'")
    s.db.execute("UPDATE ticket SET status = ?, note = ? WHERE id = 1", (res, str(a.get("note", ""))))
    s.ended = res
    return {"ticket": res}


def transfer_to_human(s: Session, a: dict):
    s.db.execute(
        "UPDATE ticket SET status = 'transferred', note = ? WHERE id = 1", (str(a.get("reason", "")),)
    )
    s.ended = "transferred"
    return {"ticket": "transferred", "message": "A team member will take over this chat."}


SYSTEM_TOOLS = [
    Tool(
        "close_ticket",
        "End the chat. Use 'resolved' when you did what the customer asked or answered their question, "
        "and 'refused' when policy does not allow the request.",
        {"resolution": ("string", "resolved or refused"), "note": ("string", "one-line summary")},
        SYSTEM,
        close_ticket,
    ),
    Tool(
        "transfer_to_human",
        "Hand the chat to a human team member when the policy says so.",
        {"reason": ("string", "why the chat needs a human")},
        SYSTEM,
        transfer_to_human,
    ),
]
