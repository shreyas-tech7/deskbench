"""Run an agent over every task for several trials, and save the results file."""

from __future__ import annotations

import json
import platform
import time
from datetime import date
from pathlib import Path

from . import __version__
from .agents.oracle import oracle_for
from .domains import all_tasks
from .episode import run_trial, transcript_bytes
from .metrics import summarize_groups

# Scripted agents. The broken and flaky ones prove that the scorer catches what it should.
SCRIPTED = {
    "oracle": {},
    "no-identity": {"skip_identity": True},
    "no-windows": {"ignore_windows": True},
    "flaky": {"skip_confirm": 0.25},  # synthetic: forgets to ask for a yes on a quarter of changes
}
BUILD_SEEDS = range(1, 9)  # the tests and the oracle checks used these while building
RUN_SEED = 101


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def run(agent_for, trials: int, seed: int, tasks=None) -> list[dict]:
    """agent_for(domain) gives a fresh agent. Trial i of every task uses seed + i."""
    out = []
    for domain, task in tasks or all_tasks():
        agent = agent_for(domain)
        for i in range(trials):
            out.append(run_trial(domain, task, agent, seed + i))
    return out


def scripted(name: str):
    return lambda domain: oracle_for(domain.name, name=name, **SCRIPTED[name])


def save(root: Path, name: str, trials: list[dict], meta: dict) -> dict:
    """Write results/<name>.json and the transcript of every failed trial."""
    tdir = root / "results" / "transcripts" / name
    if tdir.exists():
        for old in tdir.glob("*.json"):
            old.unlink()
    slim, kept = [], set()
    for t in trials:
        row = {k: v for k, v in t.items() if k != "transcript"}
        if not t["passed"] and t["task"] not in kept:  # one failed transcript per task is enough to read
            kept.add(t["task"])
            tdir.mkdir(parents=True, exist_ok=True)
            rel = f"results/transcripts/{name}/{t['task']}-seed{t['seed']}.json"
            (root / rel).write_bytes(transcript_bytes(t) + b"\n")
            row["transcript_file"] = rel
        slim.append(row)
    res = {"meta": meta, "summary": summarize_groups(trials), "trials": slim}
    (root / "results").mkdir(parents=True, exist_ok=True)
    (root / "results" / f"{name}.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    return res


def run_scripted(
    root: Path, name: str, trials: int = 4, seed: int = RUN_SEED, out: str | None = None
) -> dict:
    start = time.perf_counter()
    rows = run(scripted(name), trials, seed)
    meta = {
        "agent": name,
        "model": "none (scripted agent)",
        "synthetic": name == "flaky",
        "date": date.today().isoformat(),
        "seed": seed,
        "trials": trials,
        "version": __version__,
        "python": platform.python_version(),
        "cpu": cpu_name(),
        "seconds": round(time.perf_counter() - start, 2),
    }
    return save(root, out or name, rows, meta)
