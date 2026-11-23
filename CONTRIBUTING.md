# Contributing

Thanks for looking. This is a small project, so the rules are short.

1. Run `./init.sh` before and after a change. It installs the dev tools, runs ruff, checks links and runs the offline tests.
2. Write the test first. Each new policy rule needs one call that breaks it and one that follows it in `tests/test_policy.py`.
3. Never type a number into the README. Change the code or rerun an agent, then run `deskbench readme`.
4. Keep tests offline. `tests/conftest.py` fails any test that reaches a host other than localhost.
5. Keep secrets out of the repo. Run `gitleaks git --pre-commit --redact --staged --verbose` before you commit. Keys go in a local `.env`, which git ignores.
6. Write docs in plain words and active voice, with no em dashes and no semicolons in prose.

To add a business, follow `docs/ADD_A_DOMAIN.md`.
