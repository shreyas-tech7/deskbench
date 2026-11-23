# Interview questions and answers

Each answer points at the code and the results that back it. The numbers come from the results files:

<!-- gen:qa_numbers -->
From `results/flaky.json` (seed 101): pass^1 88.9% (85.6 to 92.2), pass^4 55.6% (42.2 to 68.9).
From `results/no-identity.json`: pass^1 13.3% (4.4 to 24.4), 135.6 violations per 100 trials.
From `results/no-windows.json`: pass^1 84.4% (73.3 to 93.3).
From `results/oracle.json`: pass^4 100.0% (100.0 to 100.0).
<!-- /gen:qa_numbers -->

**1. What does deskbench measure?**

It measures whether a support agent does the right thing to a shop's records, under a written policy, every time. A scripted customer brings a goal. The agent uses tools on a fresh SQLite copy. `scorer.score` in `src/deskbench/scorer.py` passes the trial only if the outcome matches, the named fields match, nothing else changed and no rule fired.

**2. Why does pass^k matter more than pass^1 in production?**

A support agent answers the same kind of request thousands of times. pass^1 says how often one try works. pass^k says how often k tries in a row all work, which is closer to "can I trust it with this kind of ticket". The flaky agent in `results/flaky.json` shows the gap: its pass^1 looks fine, and its pass^4 is much lower (see the numbers above). An agent that fails one chat in ten fails some customer every day.

**3. How do you compute pass^k?**

With the unbiased estimator from τ-bench. For a task with n trials and c passes, the chance that k trials drawn without replacement all pass is C(c, k) / C(n, k). `metrics.pass_hat_k` computes it per task, and `metrics.summarize` averages it over tasks. Raising pass^1 to the power k would be wrong, because it assumes every task has the same pass rate.

**4. Why score the database and not the chat text?**

The chat can sound right and do the wrong thing. "Your refund is on its way" means nothing if the refund row is missing, or if two rows changed. The database is the ground truth a shop cares about. `scorer.check_db` compares the named rows with the expected values and also flags every row that changed outside them. The ticket table records whether the chat ended resolved, refused or transferred, so the outcome is in the database too.

**5. How does the scripted user hide facts until the agent asks?**

`ScriptedUser` in `src/deskbench/user.py` is a state machine with an explicit `TRANSITIONS` table. `classify` reads the agent's message. If it contains a phrase from the domain's `fact_asks`, such as "zip" or "which box", the event is `ASKS_FACT` and the user reveals only those facts. A confirmation question gets a yes. Anything else gets the task's nudge, and after three nudges the user gives up. `tests/test_user.py` checks each transition.

**6. How do you make the user deterministic?**

Every random choice of wording comes from `random.Random(f"{task_id}:{seed}")`. The same seed gives the same words, so the same agent gives the same chat. `deskbench determinism` runs the oracle twice on every task and compares the transcripts byte for byte. `tests/test_user.py` pins the same property.

**7. How do you check the policy?**

Every tool call goes through `Dispatcher.call` in `src/deskbench/dispatcher.py`. It runs every rule of the domain on the database as it was before the call, then runs the tool. A rule is a small function that returns a message when the call breaks it. Tools stay permissive on purpose. If the tool refused a late return, the break would be hidden. Logging it lets the score show it.

**8. How do you know the tasks can be solved?**

The oracle agents in `src/deskbench/agents/oracle.py` solve every task by script. They read only the chat and the tool results, never the task's expected state. `tests/test_oracle.py` runs them on every task with two seeds, and `results/oracle.json` shows pass^4 on all 45 tasks.

**9. How do you know the scorer works?**

Broken agents. The same oracle with `skip_identity` fails every task that touches an account, and with `ignore_windows` it fails every task tagged `window`. `tests/test_broken_agents.py` checks that the failed set equals the tagged set, task by task. `tests/test_policy.py` has one call that breaks each rule and one that follows it.

**10. How does the model agent work?**

`LLMAgent` in `src/deskbench/agents/llm.py` puts the policy and the time in the system prompt and sends the tool schemas. It turns native tool calls into dispatcher calls and plain text into chat. A model that cannot call tools can answer with a JSON action, which `parse_action` reads. Tool results go back as data, never as instructions.

**11. How do record and replay work?**

`RecordClient` saves every response under a hash of the full request. If the file already exists it reuses it, so a run stopped by a rate limit resumes for free. `ReplayClient` answers only from those files and raises `MissingFixture` for anything new, so a replay can never make a live call. `tests/test_llm_agent.py` records a run against a local fake server and checks that the replay gives the same transcript.

**12. Did you run a real model?**

No. On the build day the free provider hosts were refused by the network and no key was set, so `results/record-status.json` says blocked and the README says so. Everything a model run needs is tested against a local server whose brain is the oracle. Shreyas can run it with one command once a key exists.

**13. How do you stop yourself from tuning the agent to the tasks?**

Five tasks per domain are held out and were fixed before any agent prompt existed. The results tables report dev and held-out groups apart. The result runs use seeds that no test or check used while building, and `tests/test_repo.py` enforces that.

**14. What does the interval mean?**

It is a percentile bootstrap over tasks. `metrics.interval` resamples the 45 per-task scores with replacement 2,000 times and takes the middle 95% of the means. It says how much the number would move with a different set of tasks of the same kind. When every task scores the same, the interval is one value, and the README says that this means no spread.

**15. What can this benchmark not show?**

It cannot show how an agent handles real customers, who are vaguer, change their minds and lie. The scripted user matches keywords, so it can punish a model that asks in odd words. It says yes to any confirmation, so it does not test whether the agent proposes the right change before asking. The scorer catches that at the end instead. 45 tasks give wide intervals. And no model number exists yet.

**16. How would you add a new business?**

Follow `docs/ADD_A_DOMAIN.md`: a seed file, a policy, tools, rules, tasks and an oracle. `tests/test_add_domain.py` builds a toy library in one file the same way, so the guide cannot drift from the code.
