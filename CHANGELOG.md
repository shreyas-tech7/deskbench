# Changelog

## v0.1.0-rc1 (unreleased)

Release commit: written at release time, see the last entry below.

- Three invented domains (bike parts, salon, meal kit) with a policy, a seeded SQLite database, ten tools and 15 tasks each.
- A scripted user built as an explicit state machine. The same seed gives byte-identical transcripts.
- One dispatcher that checks the policy on every tool call before it runs.
- A scorer that checks the outcome, the named fields, that nothing else changed and that no rule fired.
- Oracle agents that pass all 45 tasks, plus broken and flaky agents that prove the scorer.
- An LLM agent for any OpenAI-compatible endpoint, with record, resume and replay, and a JSON action fallback.
- pass^1 to pass^4 with the unbiased estimator and bootstrap 95% intervals over tasks.
- `deskbench` command line, generated README tables, `docs/REPORT.md` and a static results page.
