"""Every tool call goes through one dispatcher. It checks the policy, runs the tool and logs the call."""

from __future__ import annotations

import json
import sqlite3

from .core import CallCtx, Domain, Session, ToolError


class Dispatcher:
    def __init__(self, domain: Domain, db: sqlite3.Connection):
        self.domain = domain
        self.session = Session(db=db, now=domain.now)
        self.log: list[dict] = []

    @property
    def ended(self) -> str | None:
        return self.session.ended

    def call(self, name: str, args: dict | None, last_user: str = "") -> dict:
        args = args if isinstance(args, dict) else {}
        entry = {"tool": name, "args": args, "violations": [], "error": None}
        self.log.append(entry)
        tool = self.domain.tools.get(name)
        if tool is None:
            entry["error"] = f"unknown tool {name!r}"
            return {"error": entry["error"]}
        missing = [p for p in tool.params if p not in args]
        if missing:
            entry["error"] = f"missing arguments: {', '.join(missing)}"
            return {"error": entry["error"]}
        ctx = CallCtx(tool, args, self.session, last_user)
        for rule in self.domain.rules:  # checked on the state before the call runs
            msg = rule.check(ctx)
            if msg:
                entry["violations"].append({"rule": rule.id, "detail": msg})
        try:
            result = tool.fn(self.session, args)
            self.session.db.commit()
        except (ToolError, ValueError, TypeError) as e:
            self.session.db.rollback()
            entry["error"] = str(e)
            return {"error": str(e)}
        # Tool results are data for the agent, never instructions. Keep them plain JSON.
        return json.loads(json.dumps(result, default=str))

    @property
    def violations(self) -> list[dict]:
        return [dict(v, tool=e["tool"]) for e in self.log for v in e["violations"]]

    @property
    def wrong_calls(self) -> int:
        return sum(1 for e in self.log if e["error"])
