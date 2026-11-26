# Progress

## Done

- F01 to F16: three domains with 45 tasks, scorer, policy dispatcher, scripted user, oracles, broken and flaky agents, LLM agent with record, resume and replay, pass^k metrics, CLI, results files, generated README, report and page, add-a-domain guide with a toy-domain test, CI workflow, docs and study kit.
- Results at seed 101 (4 trials, 45 tasks) for oracle, no-identity, no-windows and flaky, plus an oracle rerun at seed 202.
- Record mode: blocked. No key, and the provider hosts are refused by the network (probed 2026-11-23). Written to results/record-status.json and the README.

- F16: release check in docs/RELEASE_CHECK.md. The outside check found one scorer bug, fixed with a test. Hand-off in docs/HUMAN_STEPS.md and HANDOVER.md.

## Next

- The coordinator opens the PR, merges it, creates the v0.1.0-rc1 pre-release and sets About and topics.
- Record mode once a key and network exist: docs/HUMAN_STEPS.md step 10.

## Open blockers

- Record mode: see BLOCKERS.md.

## Last ./init.sh

2026-11-23: 306 passed, ruff clean, links clean.
