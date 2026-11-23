# Handover

## Done

- All 16 features in `feature_list.json`. The release check and hand-off are written up in `docs/RELEASE_CHECK.md` and `docs/HUMAN_STEPS.md`.
- 45 tasks in three domains. The oracle passes all of them. The broken agents fail exactly their tagged tasks.
- Results at seed 101 for four scripted agents, plus an oracle rerun at seed 202.

## Next

- Record mode needs a free provider key and a network that reaches the provider. Run the commands in `docs/HUMAN_STEPS.md` step 10, then `deskbench readme` and `./init.sh`.
- Stretch: an LLM user simulator in record mode for 10 tasks, compared with the scripted user.

## Open decisions

- Whether `docs/build/BUILD_PROMPT.md` stays public.

## Exact commands

```bash
./init.sh
.venv/bin/deskbench readme --check
.venv/bin/deskbench determinism
```
