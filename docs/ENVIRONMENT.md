# Build environment

Probes from the build machine. These explain why record mode did not run.

| Host | Date | Result |
| --- | --- | --- |
| api.groq.com | 2026-11-21 and 2026-11-23 | refused by the network proxy (403) |
| openrouter.ai | 2026-11-21 and 2026-11-23 | refused by the network proxy (403) |
| huggingface.co | 2026-11-21 | refused (403) |
| api.osv.dev, semgrep.dev | 2026-11-21 | refused (403) |
| pypi.org, registry.npmjs.org (names `deskbench`, `supportbench`) | 2026-11-21 | 404, so both names were free |
| raw.githubusercontent.com | 2026-11-21 | 301 redirect |

No provider key was set in the environment, so no model request was sent. `deskbench probe` repeats the host check.

Timings in the README come from one core of the build machine's CPU, named in each results file under `meta.cpu`.
