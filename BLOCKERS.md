# Blockers

| Date | What failed | Exact error | What I did instead |
| --- | --- | --- | --- |
| 2026-11-21 | Record-mode hosts | `curl: (56) CONNECT tunnel failed, response 403` for api.groq.com and openrouter.ai. No `GROQ_API_KEY` or `OPENROUTER_API_KEY` set | Built record and replay against a local fake OpenAI server in tests. The README states that no real-model run exists. Manual step in `docs/HUMAN_STEPS.md` |
| 2026-11-21 | PR, tag, About and topics from this VM | The proxy refuses `gh pr`, tag pushes and GraphQL (per the session brief) | The coordinator opens the PR and sets About and topics. Values are in `docs/GITHUB_ABOUT.md` and `docs/topics.txt` |
| 2026-11-21 | Live bug, score 5x4=20, fixed | The confirmation rule took "Sure, my order number is 1001" as a yes, so the no-confirm broken agent passed bk02 | Dropped "sure" from the yes pattern. `test_skipping_confirmation_fails_every_write_task` found it |
| 2026-11-23 | Record-mode hosts, rechecked | `deskbench probe`: both hosts refused by the network proxy (403). No key set | Same as above. `results/record-status.json` holds the probe and the README says no model ran |
| 2026-11-23 | Review finding, score 4x4=16, fixed | `get_order {"order_id": 99999999999999999999}` raised `OverflowError` and crashed the trial | The dispatcher now treats it as a wrong call. Test in `tests/test_policy.py` |
| 2026-11-23 | Review finding, score 4x4=16, fixed | mk10 passed when the agent also paused the subscriber | The scorer now checks unnamed columns of named rows. Test in `tests/test_scorer.py` |
| 2026-11-23 | Outside check finding, score 4x4=16, fixed | sl08 passed when the agent moved booking 101 and then refused, because a `count` spec covered the row | A `count` spec now allows no edit to an existing row. Test in `tests/test_scorer.py` |
