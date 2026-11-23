# deskbench implementation plan

**Goal:** a support-agent benchmark on three invented small businesses, scored by database state, with pass^k reliability.

**Architecture:** load a domain and copy its database, start the scripted user, run the agent with tools against the copy through one dispatcher, end the chat with a ticket outcome, score the end state and the policy log, then aggregate pass^k.

**Tech stack:** Python 3.11, `sqlite3`, `urllib`, pytest, ruff. No other dependency.

## Assumptions

- "Now" is fixed at 2026-06-15 10:00 in every domain, so window rules never drift.
- The chat outcome is a database row (`ticket.status`), written by `close_ticket` or `transfer_to_human`.
- The scripted user answers a fact only when the agent's message contains one of that fact's ask phrases. It says yes only when asked to confirm.
- Trials of the oracle differ only in the user's wording, picked by the seed. The oracle is deterministic, so its pass^k is 1 by design.
- Held-out split: tasks 11 to 15 of each domain (15 tasks), fixed in `tasks.json` before any agent prompt work.

## Tasks

1. Initializer: memory files, `init.sh`, conftest network guard, CI, toolkit. Test: `./init.sh`.
2. Bike domain: `seed.sql`, `policy.md`, tools, rules, 15 tasks. Test: schema loads, every tool answers, 6 to 10 tools.
3. Scorer: field match, row counts, unexpected changes, outcome, violations. Test: hand-made before and after states.
4. Bike oracle. Test: all 15 pass.
5. Scripted user. Test: each transition in the table, facts hidden until asked, byte-identical replays.
6. Policy checker. Test: one breaking and one following call per rule.
7. Broken agents. Test: the failing set equals the tagged set.
8. Salon and meal-kit domains with oracles. Test: all 45 pass.
9. LLM agent loop, record mode, fixture replay, JSON action fallback. Test: local fake OpenAI server.
10. Metrics and report. Test: pass^k estimator against hand values, interval contains the point.
11. Record run, resumable. Blocked here (no key, hosts 403), so the README says so.
12. README, domain guide, study kit, release check, hand-off.
