"""Scores over many trials: unbiased pass^k, rates per task, and bootstrap 95% intervals over tasks."""

from __future__ import annotations

import random
from collections import defaultdict
from math import comb

KS = (1, 2, 3, 4)
BOOT = 2000


def pass_hat_k(c: int, n: int, k: int) -> float:
    """Chance that k trials drawn without replacement from n all pass, given c passed: C(c,k)/C(n,k)."""
    if k > n:
        raise ValueError(f"k={k} needs at least {k} trials, got {n}")
    return comb(c, k) / comb(n, k)


def by_task(trials: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for t in trials:
        out[t["task"]].append(t)
    return dict(sorted(out.items()))


def interval(values: list[float], boot: int = BOOT, seed: int = 0) -> tuple[float, float, float]:
    """Mean with a percentile bootstrap 95% interval, resampling tasks with replacement."""
    if not values:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)  # noqa: S311 (seeded bootstrap, not security)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(boot))
    return (sum(values) / n, means[int(0.025 * boot)], means[int(0.975 * boot) - 1])


def summarize(trials: list[dict], ks=KS, boot: int = BOOT) -> dict:
    tasks = by_task(trials)
    n = min((len(v) for v in tasks.values()), default=0)
    per = {
        "violations": [100 * sum(len(t["violations"]) for t in v) / len(v) for v in tasks.values()],
        "wrong_calls": [sum(t["wrong_calls"] for t in v) / len(v) for v in tasks.values()],
        "turns": [sum(t["turns"] for t in v) / len(v) for v in tasks.values()],
        "tokens": [sum(t["tokens"] for t in v) / len(v) for v in tasks.values()],
    }
    out = {"tasks": len(tasks), "trials_per_task": n, "pass": {}}
    for k in ks:
        if k <= n:
            vals = [pass_hat_k(sum(t["passed"] for t in v), len(v), k) for v in tasks.values()]
            out["pass"][k] = interval(vals, boot)
    for name, vals in per.items():
        out[name] = interval(vals, boot)
    return out


def summarize_groups(trials: list[dict], boot: int = BOOT) -> dict:
    groups = {"all": trials}
    for split in ("dev", "heldout"):
        groups[split] = [t for t in trials if t["split"] == split]
    for d in sorted({t["domain"] for t in trials}):
        groups[d] = [t for t in trials if t["domain"] == d]
    return {g: summarize(v, boot=boot) for g, v in groups.items() if v}
