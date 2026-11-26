# Release check

What I checked before v0.1.0-rc1, on 2026-11-23, and what I found. Every fix has a test.

| Check | Result |
| --- | --- |
| ponytail-review of `src/deskbench` | 2 must-fix items. A 20-digit order id raised `OverflowError` and crashed the trial. An extra column change on a named row passed. Both fixed, with tests in `tests/test_policy.py` and `tests/test_scorer.py` |
| gitleaks on the full history | `gitleaks git -v .`: no leaks found. The pre-commit hook ran on every commit |
| pip-audit | No known vulnerabilities in the locked dev tools. deskbench itself is not on PyPI, so it has no entry to audit |
| ruff S (security rules) | 4 findings: one misplaced `noqa` and three uses of `random` for scripted wording. Fixed. The `random` uses are for test data, not secrets, and carry a `noqa: S311` note |
| actionlint on `.github/workflows/ci.yml` | Clean |
| Link check (`scripts/check_links.py`) | 0 problems. 4 external links were not fetched, because the network refuses most hosts here |
| humanizer pass | README, WALKTHROUGH, INTERVIEW_QA and ADD_A_DOMAIN reviewed and edited. `tests/test_repo.py` checks the writing rules on every doc |
| Outside check by a fresh subagent | It cloned the repo, ran `./init.sh` (302 passed) and checked Done-means 1 to 7. Items 1, 2, 3, 5, 6 and 7 pass. Item 4 passes only through its "blocked" clause. It found one bug, fixed below |

## The outside check's bug

Task sl08 expects Iris's color booking to be refused. An agent that verified Iris, moved booking 101 and then closed the ticket as refused still passed. The task names that booking only with a `count` spec, and the scorer let a counted row change freely. sl09 and mk03 had the same gap.

The fix: a `count` spec checks how many rows exist, and it allows no edit to an existing row. Only a spec with `fields` allows a column to change. `test_edit_to_a_row_named_only_by_count_fails` in `tests/test_scorer.py` covers it. I reran all four scripted agents after the fix, and every score stayed the same, because no scripted agent made such a change.

## Not checked

- CI on GitHub. This machine has no `gh` and cannot read the Actions page. The coordinator or Shreyas checks the first run.
- A real model. Record mode is blocked, see `BLOCKERS.md`.

## Local run

`./init.sh` on 2026-11-23 after every fix: 306 passed, ruff and format clean, links clean. `deskbench readme --check`: up to date. `deskbench determinism`: 45 of 45 byte-identical.
