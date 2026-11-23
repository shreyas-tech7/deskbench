"""Score a trial from state: the final database, the ticket outcome and the policy log. No text is judged."""

from __future__ import annotations

import sqlite3


def snapshot(db: sqlite3.Connection) -> dict[str, dict[int, dict]]:
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    return {
        t: {
            r["_rid"]: {k: r[k] for k in r.keys() if k != "_rid"}
            for r in db.execute(f'SELECT rowid AS _rid, * FROM "{t}"')  # noqa: S608 (table names come from sqlite_master)
        }
        for t in tables
        if t != "ticket"
    }


def _matches(r: dict, where: dict) -> bool:
    return all(r.get(k) == v for k, v in where.items())


def check_db(before: dict, after: dict, specs: list[dict]) -> list[str]:
    """Each spec names rows by `where` and checks `fields` or a row `count`. Any other change fails."""
    problems = []
    for s in specs:
        found = [r for r in after.get(s["table"], {}).values() if _matches(r, s["where"])]
        if "count" in s:
            if len(found) != s["count"]:
                problems.append(f"{s['table']} {s['where']}: expected {s['count']} rows, found {len(found)}")
            continue
        if len(found) != 1:
            problems.append(f"{s['table']} {s['where']}: expected 1 row, found {len(found)}")
            continue
        for k, v in s["fields"].items():
            if found[0].get(k) != v:
                problems.append(f"{s['table']} {s['where']}: {k} is {found[0].get(k)!r}, expected {v!r}")
    for table in after:
        old, new = before.get(table, {}), after[table]
        for rid in set(old) | set(new):
            if old.get(rid) == new.get(rid):
                continue
            rec = new.get(rid) or old[rid]
            cover = [s for s in specs if s["table"] == table and _matches(rec, s["where"])]
            if not cover:
                problems.append(f"unexpected change in {table}: {rec}")
            elif rid in old and rid in new and all("fields" in s for s in cover):
                named = {k for s in cover for k in (*s["where"], *s["fields"])}
                extra = sorted(k for k in new[rid] if new[rid][k] != old[rid].get(k) and k not in named)
                if extra:
                    problems.append(f"unexpected change in {table} {cover[0]['where']}: {', '.join(extra)}")
    return problems


def outcome(db: sqlite3.Connection) -> str:
    return db.execute("SELECT status FROM ticket WHERE id = 1").fetchone()[0]


def score(task: dict, before: dict, db: sqlite3.Connection, violations: list[dict]) -> dict:
    got = outcome(db)
    problems = check_db(before, snapshot(db), task["expected"]["db"])
    if got != task["expected"]["outcome"]:
        problems.insert(0, f"outcome is {got}, expected {task['expected']['outcome']}")
    problems += [f"policy {v['rule']}: {v['detail']}" for v in violations]
    return {"passed": not problems, "outcome": got, "problems": problems}
