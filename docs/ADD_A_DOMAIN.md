# Add a domain

A domain is one invented business: a policy, a seeded database, tools, rules and tasks. This guide adds a small library as the example. The same library, in one file, lives in `tests/test_add_domain.py`, so the test suite fails if this guide stops matching the code.

## 1. Make the folder

```text
src/deskbench/domains/library/
    __init__.py   tools, rules and the DOMAIN object
    seed.sql      tables and rows
    policy.md     the rules in plain English, under 70 lines
    tasks.json    15 tasks, 10 dev and 5 held out
```

## 2. Seed the database

Write `CREATE TABLE` and `INSERT` lines in `seed.sql`. Invent every name and value. Each trial runs on a fresh in-memory copy, and `deskbench.core` adds the `ticket` table itself, so leave it out.

## 3. Write the policy

Put one rule per line or short paragraph in `policy.md`. The agent reads this file in its system prompt. Two rules hold in every domain and come from `deskbench.policy.COMMON_RULES`: verify the customer before you touch their account, and get an explicit yes before any change.

## 4. Write the tools

Each tool is a `Tool(name, description, params, kind, fn, owner)` in `__init__.py`.

- `kind` is one of `LOOKUP` (find a customer id), `VERIFY` (check a second fact and set `session.verified`), `PUBLIC`, `READ` or `WRITE`.
- `owner(db, args)` returns the customer id that a `READ` or `WRITE` call touches. The identity rule uses it.
- A tool raises `ToolError` only for bad data, such as an unknown id. It does not enforce the policy. A rule does that, so a break is logged instead of hidden.
- End the list with `*SYSTEM_TOOLS`, which adds `close_ticket` and `transfer_to_human`.
- Keep the total between 6 and 10 tools.

## 5. Write the rules

A rule is `Rule(id, text, check)`. `check(ctx)` runs before the tool, on the database as it was. It returns a short message when the call breaks the rule, and `None` when it follows it. `ctx.tool`, `ctx.args`, `ctx.db`, `ctx.session` and `ctx.last_user` are all there.

```python
def rule_renew(ctx):
    if ctx.tool.name == "renew_loan":
        r = row(ctx.db, "SELECT renewals FROM loans WHERE id = ?", ctx.args.get("loan_id"))
        if r and r["renewals"] >= 2:
            return "renewed a loan that was already renewed twice"
    return None

RULES = COMMON_RULES + [Rule("LB_RENEW", "Renew a loan at most twice.", rule_renew)]
```

## 6. Write the tasks

Each task in `tasks.json` has an `id`, a `split` (`dev` or `heldout`), an `intent`, `tags`, a `goal`, three `opening` lines, a `nudge`, the `facts` the user knows, and the `expected` result. The expected result names the outcome (`resolved`, `refused` or `transferred`) and the rows to check.

```json
{"table": "loans", "where": {"id": 10}, "fields": {"renewals": 1}}
{"table": "loans", "where": {"member_id": 2}, "count": 1}
```

Any changed row that no `where` covers fails the trial. Tag a task `identity`, `write` or `window` when the matching broken agent should fail it.

## 7. Tell the user how facts are asked

The `Domain` object takes `fact_labels` (how the user names each fact), `fact_asks` (phrases in the agent's message that ask for it) and, if you like, `fact_templates` (how the user says it). The user reveals a fact only when one of its phrases appears.

## 8. Write the oracle

Subclass `ScriptAgent` in `src/deskbench/agents/oracle.py`. Write `script(opening)` as a generator. `yield from self.identify(...)` runs the two-step check. `yield from self.confirm(...)`, `self.call(...)`, `self.finish(...)`, `self.refuse(...)` and `self.transfer(...)` do the rest. The oracle reads only the chat and the tool results, never the task's expected state. Add it to `ORACLES`.

## 9. Register and test

1. Import the module in `src/deskbench/domains/__init__.py` and add it to `DOMAINS`.
2. Add one breaking call and one following call per rule to `CASES` in `tests/test_policy.py`.
3. Run `./init.sh`. The oracle test, the broken-agent test and the determinism test pick up the new tasks by themselves.
4. Run `deskbench run oracle` and the other agents, then `deskbench readme`.
