# deskbench report

`deskbench readme` writes this file from `results/`. Do not edit it by hand.

pass^k is the chance that k trials of the same task all pass, estimated per task as C(c, k) / C(n, k) and averaged over tasks. Brackets hold a bootstrap 95% interval over tasks.

## Runs

- `oracle`: run of 2026-11-23, model none (scripted agent), seed 101 to 104, 45 tasks with 4 trials each, file `results/oracle.json`.
- `no-identity`: run of 2026-11-23, model none (scripted agent), seed 101 to 104, 45 tasks with 4 trials each, file `results/no-identity.json`.
- `no-windows`: run of 2026-11-23, model none (scripted agent), seed 101 to 104, 45 tasks with 4 trials each, file `results/no-windows.json`.
- `flaky`: run of 2026-11-23, model none (scripted agent), seed 101 to 104, 45 tasks with 4 trials each, file `results/flaky.json`. Synthetic agent, not a model.

## Results

| Agent | pass^1 | pass^2 | pass^3 | pass^4 | Violations per 100 trials | Wrong tool calls per task |
| --- | --- | --- | --- | --- | --- | --- |
| Oracle (scripted, follows policy) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 0.0 (0.0 to 0.0) | 0.00 (0.00 to 0.00) |
| Broken: skips the identity check | 13.3% (4.4 to 24.4) | 13.3% (4.4 to 24.4) | 13.3% (4.4 to 24.4) | 13.3% (4.4 to 24.4) | 135.6 (113.3 to 155.6) | 0.00 (0.00 to 0.00) |
| Broken: ignores time windows | 84.4% (73.3 to 93.3) | 84.4% (73.3 to 93.3) | 84.4% (73.3 to 93.3) | 84.4% (73.3 to 93.3) | 15.6 (6.7 to 26.7) | 0.00 (0.00 to 0.00) |
| Flaky: skips the yes on 1 in 4 changes (synthetic) | 88.9% (85.6 to 92.2) | 77.8% (71.1 to 84.4) | 66.7% (56.7 to 76.7) | 55.6% (42.2 to 68.9) | 11.1 (7.8 to 14.4) | 0.00 (0.00 to 0.00) |

## Dev and held-out tasks

| Agent | Dev pass^1 | Dev pass^4 | Held-out pass^1 | Held-out pass^4 |
| --- | --- | --- | --- | --- |
| Oracle (scripted, follows policy) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) |
| Broken: skips the identity check | 0.0% (0.0 to 0.0) | 0.0% (0.0 to 0.0) | 40.0% (13.3 to 66.7) | 40.0% (13.3 to 66.7) |
| Broken: ignores time windows | 80.0% (63.3 to 93.3) | 80.0% (63.3 to 93.3) | 93.3% (80.0 to 100.0) | 93.3% (80.0 to 100.0) |
| Flaky: skips the yes on 1 in 4 changes (synthetic) | 86.7% (82.5 to 90.8) | 46.7% (30.0 to 63.3) | 93.3% (86.7 to 98.3) | 73.3% (46.7 to 93.3) |

## By domain

| Agent | Bike parts pass^1 | Bike parts pass^4 | Salon pass^1 | Salon pass^4 | Meal kit pass^1 | Meal kit pass^4 |
| --- | --- | --- | --- | --- | --- | --- |
| Oracle (scripted, follows policy) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) | 100.0% (100.0 to 100.0) |
| Broken: skips the identity check | 13.3% (0.0 to 33.3) | 13.3% (0.0 to 33.3) | 13.3% (0.0 to 33.3) | 13.3% (0.0 to 33.3) | 13.3% (0.0 to 33.3) | 13.3% (0.0 to 33.3) |
| Broken: ignores time windows | 86.7% (66.7 to 100.0) | 86.7% (66.7 to 100.0) | 80.0% (60.0 to 100.0) | 80.0% (60.0 to 100.0) | 86.7% (66.7 to 100.0) | 86.7% (66.7 to 100.0) |
| Flaky: skips the yes on 1 in 4 changes (synthetic) | 90.0% (83.3 to 96.7) | 60.0% (33.3 to 86.7) | 88.3% (81.7 to 95.0) | 53.3% (26.7 to 80.0) | 88.3% (81.7 to 95.0) | 53.3% (26.7 to 80.0) |

## Cost

| Agent | Tokens per task | Turns per task | Wall time for the run |
| --- | --- | --- | --- |
| Oracle (scripted, follows policy) | 0 (0 to 0) | 9.2 (8.3 to 9.9) | 0.21 s |
| Broken: skips the identity check | 0 (0 to 0) | 7.5 (6.8 to 8.2) | 0.23 s |
| Broken: ignores time windows | 0 (0 to 0) | 9.5 (8.6 to 10.4) | 0.22 s |
| Flaky: skips the yes on 1 in 4 changes (synthetic) | 0 (0 to 0) | 9.0 (8.1 to 9.7) | 0.19 s |

## Record mode

Record mode did not run. Checked on 2026-11-23 for model `llama-3.1-8b-instant`: no GROQ_API_KEY in the environment, so no request was sent. A probe of the provider hosts on that day gave: groq refused by the network proxy (403), openrouter refused by the network proxy (403). So no row on this page comes from a language model, and Done-means item 4 is open. The LLM agent in `src/deskbench/agents/llm.py` passes all 45 tasks against a fake local server in `tests/test_llm_agent.py`, so the loop, the tool calls, the JSON fallback, record and replay all run. `docs/HUMAN_STEPS.md` has the command to run once a free key exists.

## Failures

Each line names the rules that fired, or the first scoring problem when no rule fired. The link opens the first failed trial of that task.

### Oracle (scripted, follows policy)

- None.

### Broken: skips the identity check

- `bk01` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk01-seed101.json)
- `bk02` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk02-seed101.json)
- `bk03` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk03-seed101.json)
- `bk04` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk04-seed101.json)
- `bk05` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk05-seed101.json)
- `bk06` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk06-seed101.json)
- `bk07` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk07-seed101.json)
- `bk08` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk08-seed101.json)
- `bk09` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk09-seed101.json)
- `bk10` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk10-seed101.json)
- `bk11` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk11-seed101.json)
- `bk13` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk13-seed101.json)
- `bk15` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/bk15-seed101.json)
- `mk01` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk01-seed101.json)
- `mk02` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk02-seed101.json)
- `mk03` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk03-seed101.json)
- `mk04` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk04-seed101.json)
- `mk05` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk05-seed101.json)
- `mk06` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk06-seed101.json)
- `mk07` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk07-seed101.json)
- `mk08` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk08-seed101.json)
- `mk09` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk09-seed101.json)
- `mk10` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk10-seed101.json)
- `mk13` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk13-seed101.json)
- `mk14` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk14-seed101.json)
- `mk15` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/mk15-seed101.json)
- `sl01` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl01-seed101.json)
- `sl02` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl02-seed101.json)
- `sl03` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl03-seed101.json)
- `sl04` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl04-seed101.json)
- `sl05` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl05-seed101.json)
- `sl06` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl06-seed101.json)
- `sl07` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl07-seed101.json)
- `sl08` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl08-seed101.json)
- `sl09` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl09-seed101.json)
- `sl10` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl10-seed101.json)
- `sl12` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl12-seed101.json)
- `sl13` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl13-seed101.json)
- `sl15` failed 4 of 4 trials: IDENTITY. [Transcript](../results/transcripts/no-identity/sl15-seed101.json)

### Broken: ignores time windows

- `bk05` failed 4 of 4 trials: BK_WINDOW. [Transcript](../results/transcripts/no-windows/bk05-seed101.json)
- `bk06` failed 4 of 4 trials: BK_WINDOW. [Transcript](../results/transcripts/no-windows/bk06-seed101.json)
- `mk02` failed 4 of 4 trials: MK_CREDIT. [Transcript](../results/transcripts/no-windows/mk02-seed101.json)
- `mk06` failed 4 of 4 trials: MK_CUTOFF. [Transcript](../results/transcripts/no-windows/mk06-seed101.json)
- `sl02` failed 4 of 4 trials: SL_DEPOSIT. [Transcript](../results/transcripts/no-windows/sl02-seed101.json)
- `sl06` failed 4 of 4 trials: SL_RESCHEDULE. [Transcript](../results/transcripts/no-windows/sl06-seed101.json)
- `sl12` failed 4 of 4 trials: SL_RESCHEDULE. [Transcript](../results/transcripts/no-windows/sl12-seed101.json)

### Flaky: skips the yes on 1 in 4 changes (synthetic)

- `bk01` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk01-seed103.json)
- `bk02` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk02-seed103.json)
- `bk03` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk03-seed103.json)
- `bk08` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk08-seed103.json)
- `bk09` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk09-seed103.json)
- `bk13` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/bk13-seed103.json)
- `mk01` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk01-seed103.json)
- `mk04` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk04-seed103.json)
- `mk05` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk05-seed103.json)
- `mk07` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk07-seed103.json)
- `mk10` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk10-seed103.json)
- `mk13` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk13-seed103.json)
- `mk14` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/mk14-seed103.json)
- `sl01` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl01-seed103.json)
- `sl02` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl02-seed103.json)
- `sl03` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl03-seed103.json)
- `sl04` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl04-seed103.json)
- `sl07` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl07-seed103.json)
- `sl10` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl10-seed103.json)
- `sl13` failed 1 of 4 trials: CONFIRM. [Transcript](../results/transcripts/flaky/sl13-seed103.json)
