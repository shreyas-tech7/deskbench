"""Command line: deskbench run | llm | show | determinism | probe | readme."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from . import __version__
from .agents.llm import PROVIDERS, HttpClient, LLMAgent, RecordClient, ReplayClient
from .bench import RUN_SEED, SCRIPTED, cpu_name, run_scripted, save, scripted
from .domains import DOMAINS, all_tasks
from .episode import run_trial, transcript_bytes
from .readme import RECORD, write

ROOT = Path.cwd()


def _fmt(s: dict) -> str:
    p = " ".join(f"pass^{k}={100 * v[0]:.1f}%" for k, v in s["pass"].items())
    return f"{p} violations/100={s['violations'][0]:.1f} wrong_calls={s['wrong_calls'][0]:.2f} turns={s['turns'][0]:.1f}"


def cmd_run(a) -> int:
    res = run_scripted(ROOT, a.agent, a.trials, a.seed, a.name)
    for g in ("all", "dev", "heldout"):
        print(f"{a.agent} {g:8} {_fmt(res['summary'][g])}")
    print(f"wrote results/{a.name or a.agent}.json")
    return 0


def probe(url: str) -> str:
    try:
        with urllib.request.urlopen(url + "/models", timeout=10) as r:  # noqa: S310 (fixed https provider URL)
            return f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except (urllib.error.URLError, OSError) as e:
        why = str(getattr(e, "reason", e))
        return "refused by the network proxy (403)" if "403" in why else f"no connection ({why[:80]})"


def cmd_probe(a) -> int:
    for name, (base, _, _) in PROVIDERS.items():
        print(f"{name}: {base} -> {probe(base)}")
    return 0


def _client(a):
    if a.base_url:
        base, var, model = a.base_url, a.key_env, a.model
    else:
        base, var, model = PROVIDERS[a.provider]
        model = a.model or model
    return base, var, model


def cmd_llm(a) -> int:
    base, var, model = _client(a)
    fixtures = ROOT / a.fixtures
    (ROOT / "results").mkdir(exist_ok=True)
    if a.mode == "replay":
        client = ReplayClient(fixtures, model)
    else:
        key = os.environ.get(var or "")
        if not key:
            status = {
                "status": "blocked",
                "date": date.today().isoformat(),
                "provider": a.provider if not a.base_url else base,
                "model": model,
                "reason": f"no {var} in the environment, so no request was sent.",
                "probe": {n: probe(b) for n, (b, _, _) in PROVIDERS.items()} if a.probe else {},
            }
            (ROOT / RECORD).write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
            print(f"record mode blocked: {status['reason']} Wrote {RECORD}.", file=sys.stderr)
            return 2
        client = RecordClient(HttpClient(base, key, model), fixtures)
    tasks = [(d, t) for d, t in all_tasks() if a.split == "all" or t["split"] == a.split][: a.limit or None]
    rows, stopped = [], None
    for domain, task in tasks:
        agent = LLMAgent(client)
        try:
            done = [run_trial(domain, task, agent, a.seed + i) for i in range(a.trials)]
        except (
            OSError,
            KeyError,
            ValueError,
        ) as e:  # rate limit, network, or a fixture that was never recorded
            stopped = f"{task['id']}: {type(e).__name__}: {e}"
            break
        rows += done
    name = "llm-" + "".join(c if c.isalnum() else "-" for c in model).strip("-")
    meta = {
        "agent": name,
        "model": model,
        "mode": a.mode,
        "synthetic": False,
        "date": date.today().isoformat(),
        "seed": a.seed,
        "trials": a.trials,
        "tasks_asked": len(tasks),
        "tasks_done": len(rows) // a.trials if a.trials else 0,
        "stopped": stopped,
        "version": __version__,
        "cpu": cpu_name(),
    }
    if rows:
        res = save(ROOT, name, rows, meta)
        print(f"{name} {_fmt(res['summary']['all'])}")
    if a.mode == "record":
        status = {
            "status": "ran",
            "date": meta["date"],
            "model": model,
            "results": f"results/{name}.json",
            **meta,
        }
        (ROOT / RECORD).write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
    if stopped:
        print(f"stopped after {meta['tasks_done']} of {len(tasks)} tasks: {stopped}", file=sys.stderr)
    return 1 if stopped and not rows else 0


def cmd_show(a) -> int:
    domain = next(d for d in DOMAINS.values() for t in d.tasks if t["id"] == a.task)
    trial = run_trial(domain, domain.task(a.task), scripted(a.agent)(domain), a.seed)
    for m in trial["transcript"]:
        if m["role"] == "call":
            print(
                f"  [tool] {m['tool']}({json.dumps(m['args'], sort_keys=True)}) -> {json.dumps(m['result'], sort_keys=True)}"
            )
        else:
            print(f"{m['role']:>5}: {m['text']}")
    v = ", ".join(x["rule"] for x in trial["violations"]) or "none"
    print(f"\nresult: {'PASS' if trial['passed'] else 'FAIL'}, outcome {trial['outcome']}, violations {v}")
    for p in trial["problems"]:
        print(f"  problem: {p}")
    return 0


def cmd_determinism(a) -> int:
    same = 0
    tasks = all_tasks()
    for domain, task in tasks:
        runs = [
            transcript_bytes(run_trial(domain, task, scripted("oracle")(domain), a.seed)) for _ in range(2)
        ]
        same += runs[0] == runs[1]
    print(f"seed {a.seed}: {same} of {len(tasks)} oracle transcripts byte-identical across two runs")
    return 0 if same == len(tasks) else 1


def cmd_readme(a) -> int:
    stale = write(ROOT, check=a.check)
    if a.check and stale:
        print("out of date: " + ", ".join(stale) + ". Run `deskbench readme`.", file=sys.stderr)
        return 1
    print("up to date" if a.check else "wrote " + (", ".join(stale) or "nothing, already up to date"))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="deskbench", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a scripted agent on all 45 tasks and write results/<agent>.json")
    r.add_argument("agent", choices=sorted(SCRIPTED))
    r.add_argument("--trials", type=int, default=4)
    r.add_argument("--seed", type=int, default=RUN_SEED)
    r.add_argument("--name", help="results file name, default the agent name")
    r.set_defaults(fn=cmd_run)

    m = sub.add_parser("llm", help="run the LLM agent in record or replay mode")
    m.add_argument("--provider", choices=sorted(PROVIDERS), default="groq")
    m.add_argument("--base-url", help="any OpenAI-compatible endpoint, https or 127.0.0.1")
    m.add_argument("--model")
    m.add_argument("--key-env", default="OPENAI_API_KEY", help="env var with the key, for --base-url")
    m.add_argument("--mode", choices=["record", "replay"], default="replay")
    m.add_argument("--fixtures", default="fixtures")
    m.add_argument("--split", choices=["all", "dev", "heldout"], default="all")
    m.add_argument("--limit", type=int, default=0, help="first N tasks only")
    m.add_argument("--trials", type=int, default=4)
    m.add_argument("--seed", type=int, default=RUN_SEED)
    m.add_argument("--probe", action="store_true", help="when blocked, also probe the provider hosts")
    m.set_defaults(fn=cmd_llm)

    s = sub.add_parser("show", help="print one trial's transcript")
    s.add_argument("task")
    s.add_argument("--agent", choices=sorted(SCRIPTED), default="oracle")
    s.add_argument("--seed", type=int, default=1)
    s.set_defaults(fn=cmd_show)

    d = sub.add_parser("determinism", help="check that a seed gives byte-identical oracle transcripts")
    d.add_argument("--seed", type=int, default=RUN_SEED)
    d.set_defaults(fn=cmd_determinism)

    sub.add_parser("probe", help="check whether the free provider hosts answer").set_defaults(fn=cmd_probe)

    w = sub.add_parser(
        "readme", help="write the README blocks, docs/REPORT.md and docs/index.html from results/"
    )
    w.add_argument("--check", action="store_true")
    w.set_defaults(fn=cmd_readme)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
