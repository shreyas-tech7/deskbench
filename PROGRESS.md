# Progress

## Done

- F01 to F15: three domains with 45 tasks, scorer, policy dispatcher, scripted user, oracles, broken and flaky agents, LLM agent with record, resume and replay, pass^k metrics, CLI, results files, generated README, report and page, add-a-domain guide with a toy-domain test, CI workflow, docs and study kit.
- Results at seed 101 (4 trials, 45 tasks) for oracle, no-identity, no-windows and flaky, plus an oracle rerun at seed 202.
- Record mode: blocked. No key, and the provider hosts are refused by the network (probed 2026-11-23). Written to results/record-status.json and the README.

## Next

- F16: release check (ponytail-review, gitleaks on history, pip-audit, ruff S, actionlint, links, humanizer, outside-check subagent), docs/RELEASE_CHECK.md, HUMAN_STEPS, COWORK_PROMPT, CHANGELOG SHA, HANDOVER.

## Open blockers

- Record mode: see BLOCKERS.md.

## Last ./init.sh

2026-11-23: 300 passed, ruff clean, links clean.
