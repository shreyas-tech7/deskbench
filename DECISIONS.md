# Decisions

- 2026-11-21 Name: `deskbench`. PyPI and npm both answer 404 for `deskbench` and `supportbench` (checked 2026-11-21). The repo name matches, so no rename.
- 2026-11-21 Branch: the system allows pushes only to `claude/project-thread-6e5u85`, so I build there instead of `claude/build-deskbench` (session brief rule 11).
- 2026-11-21 Plan: wrote `docs/PLAN.md` in the writing-plans layout by hand, with no question rounds, to save tokens. The brief is the spec.
- 2026-11-21 Ticket outcome lives in the database. Options: detect refusals in chat text, or make the agent close a ticket. I picked a `ticket` table that `close_ticket` and `transfer_to_human` write, so the database state decides even the chat outcome and no text is judged.
- 2026-11-21 Tools are permissive. They reject bad data (unknown id, too many units) but not policy breaks. The dispatcher checks policy before each call and logs violations. Options: tools that refuse policy breaks. That would hide agent mistakes, the way tau-bench keeps policy in the prompt.
- 2026-11-21 A trial passes only if the outcome matches, every named field matches, no other row changed and no policy rule fired. The "no other row changed" check catches extra writes that a field match alone would miss.
- 2026-11-21 Identity is two steps: `find_*` looks up an id, `verify_*` checks a second fact. Options: one verify tool. Two steps let a broken agent skip the check and still act, which the brief's broken-agent test needs.
- 2026-11-21 The oracle reads the customer's words and calls tools. It never reads `expected`. Options: replay an annotated action list. A scripted agent that applies the policy finds wrong or impossible tasks, a replay would not.
- 2026-11-21 Confirmation rule: a write passes only if the customer's message right before it starts with a yes. The scripted user says yes only when asked to confirm.
- 2026-11-21 Fixed "now" per domain (2026-06-15 10:00) so every window rule gives the same answer on every day.
