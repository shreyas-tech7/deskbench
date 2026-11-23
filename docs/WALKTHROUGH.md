# Walkthrough

This is a tour of every file. Each sentence says one thing.

## The big picture

A task is one customer with one goal. The customer is a script. The agent talks to the customer and calls tools. The tools change a small SQLite database. At the end, the code looks at the database. If it matches the task's expected state, and no rule was broken, the trial passes. Many trials make a score.

## Top folder

- `README.md` is the front page. Its number blocks are written by code.
- `init.sh` sets up the virtual environment and runs every check. Run it before and after a change.
- `pyproject.toml` names the package, the `deskbench` command and the dev tools.
- `LICENSE` is the MIT license.
- `CHANGELOG.md` lists what each release added.
- `CONTRIBUTING.md` has the short rules for changes.
- `.env.example` shows the key names for record mode. It holds no keys.
- `.pre-commit-config.yaml` runs gitleaks before each commit.
- `PROJECT_CONTEXT.md`, `PROGRESS.md`, `feature_list.json`, `DECISIONS.md`, `BLOCKERS.md` and `HANDOVER.md` are the build's memory. They say what the project is, what is done, why each choice was made and what is stuck.
- `CLAUDE.md` tells a coding agent which files to read first.

## The package: `src/deskbench/`

- `core.py` holds the building blocks. A `Tool` has a name, parameters, a kind and a function. A `Rule` has an id, a sentence and a check. A `Domain` bundles one business. A `Session` holds the database, the time and who is verified.
- `policy.py` holds the two rules every domain shares. `identity` fires when a call touches an account before the check, or touches someone else's account. `confirmation` fires when a change runs without a yes in the customer's last message.
- `dispatcher.py` is the only door to the tools. `Dispatcher.call` checks every rule first, on the database as it was. Then it runs the tool. A tool error rolls the change back. Every call goes into a log.
- `scorer.py` decides pass or fail. `snapshot` copies every table. `check_db` compares the end state with the task's expected rows. It also flags any row that changed outside those rows. `score` adds the outcome check and the violations.
- `user.py` is the scripted customer. `TRANSITIONS` is a table from (state, event) to (next state, action). `classify` reads the agent's message and picks the event. The customer gives a fact only when the message asks for it.
- `episode.py` runs one trial. `run_trial` makes a fresh database, a dispatcher and a user. It passes messages back and forth until the chat ends. Then it scores.
- `metrics.py` turns trials into numbers. `pass_hat_k` is C(c, k) / C(n, k). `interval` is a bootstrap over tasks. `summarize_groups` gives all tasks, dev, held out and each domain.
- `bench.py` runs a scripted agent over all 45 tasks and saves `results/<name>.json`. It saves one failed transcript per task.
- `readme.py` writes the README blocks, `docs/REPORT.md` and `docs/index.html` from the results files.
- `cli.py` is the `deskbench` command. It has `run`, `llm`, `show`, `determinism`, `probe` and `readme`.

## The agents: `src/deskbench/agents/`

- `oracle.py` has one scripted agent per domain. Each is a Python generator. It reads only the chat and the tool results. It never looks at the task's answer. Flags turn it into a broken agent: `skip_identity`, `ignore_windows` and `skip_confirm`.
- `llm.py` is the model agent. `LLMAgent` sends the policy, the tools and the chat to any OpenAI-compatible endpoint. `HttpClient` makes the call and retries on a rate limit. `RecordClient` saves each answer under a hash of the request. `ReplayClient` answers only from saved files. `parse_action` reads a plain JSON action when a model cannot call tools.

## The businesses: `src/deskbench/domains/`

Each folder has the same four files.

- `policy.md` is the one-page policy in plain English. The model agent reads it.
- `seed.sql` creates the tables and the invented rows.
- `tasks.json` has 15 tasks. Ten are for development and five are held out.
- `__init__.py` has the tools, the domain rules and the `DOMAIN` object.

`bikeparts` is Spoke & Sprocket. Its rules cover cancels, the 30-day window, final sale and like-for-like exchanges. `salon` is Clip & Curl. Its rules cover deposits, the one-move limit, senior stylists and no-shows. `mealkit` is Forkful. Its rules cover active plans, pause length, the skip cutoff and credits.

## Tests: `tests/`

- `conftest.py` blocks any network call to a host that is not local. `test_network_guard.py` proves it.
- `test_domains.py` checks each domain's shape and tasks.
- `test_scorer.py` checks pass and fail cases of the scorer by hand.
- `test_policy.py` has one breaking call and one following call for every rule.
- `test_user.py` checks every transition of the user and the byte-identical transcripts.
- `test_oracle.py` runs the oracle on every task.
- `test_broken_agents.py` checks that each broken agent fails exactly the tasks it should.
- `test_llm_agent.py` runs the model agent over HTTP against `fake_llm.py`, a local server whose brain is the oracle.
- `test_metrics.py` checks pass^k and the intervals against hand values.
- `test_cli.py` runs each command in a temp folder.
- `test_add_domain.py` builds the toy library from the guide.
- `test_repo.py` checks the README order, the generated numbers, the writing rules and the shipped files.

## Results and docs

- `results/*.json` are the runs behind every number. `results/transcripts/` holds failed chats. `results/record-status.json` says whether a model ran.
- `docs/REPORT.md` is the full report. `docs/index.html` is the same as a page.
- `docs/DEMO.md` is a real terminal session.
- `docs/ADD_A_DOMAIN.md` shows how to add a business.
- `docs/INTERVIEW_QA.md` has questions and answers for interviews.
- `docs/HUMAN_STEPS.md` lists what only Shreyas can do.
- `docs/build/BUILD_PROMPT.md` is the brief the agents built from.
- `scripts/check_links.py` checks every link. `scripts/make_social_preview.py` draws `docs/social-preview.png`.
