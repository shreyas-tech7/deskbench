"""Write the number blocks in the README and docs, plus docs/REPORT.md and docs/index.html, from results/.

Nobody types a number into the README. Each block sits between `<!-- gen:NAME -->` and
`<!-- /gen:NAME -->`, and this module rewrites it.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ORDER = ["oracle", "no-identity", "no-windows", "flaky"]
SECOND = "oracle-seed202"
RECORD = "results/record-status.json"
FILES = ["README.md", "docs/INTERVIEW_QA.md"]
BLOCK = re.compile(r"(<!-- gen:(\w+) -->\n)(.*?)(<!-- /gen:\2 -->)", re.S)
LABEL = {
    "oracle": "Oracle (scripted, follows policy)",
    "no-identity": "Broken: skips the identity check",
    "no-windows": "Broken: ignores time windows",
    "flaky": "Flaky: skips the yes on 1 in 4 changes (synthetic)",
}
DOMAIN_LABEL = {"bikeparts": "Bike parts", "salon": "Salon", "mealkit": "Meal kit"}


def load(root: Path, name: str) -> dict:
    return json.loads((root / "results" / f"{name}.json").read_text())


def agents(root: Path) -> list[str]:
    llm = sorted(p.stem for p in (root / "results").glob("llm-*.json"))
    return ORDER + llm


def pct(v) -> str:
    return f"{100 * v[0]:.1f}% ({100 * v[1]:.1f} to {100 * v[2]:.1f})"


def num(v, d=1) -> str:
    return f"{v[0]:.{d}f} ({v[1]:.{d}f} to {v[2]:.{d}f})"


def _table(head: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"] + [
        "| " + " | ".join(r) + " |" for r in rows
    ]


def meta_line(res: dict, name: str) -> str:
    m = res["meta"]
    s = res["summary"]["all"]
    tag = " Synthetic agent, not a model." if m.get("synthetic") else ""
    return (
        f"`{name}`: run of {m['date']}, model {m['model']}, seed {m['seed']} to {m['seed'] + m['trials'] - 1}, "
        f"{s['tasks']} tasks with {m['trials']} trials each, file `results/{name}.json`.{tag}"
    )


def main_table(root: Path) -> list[str]:
    head = [
        "Agent",
        "pass^1",
        "pass^2",
        "pass^3",
        "pass^4",
        "Violations per 100 trials",
        "Wrong tool calls per task",
    ]
    rows = []
    for n in agents(root):
        s = load(root, n)["summary"]["all"]
        rows.append(
            [LABEL.get(n, f"`{n}`")]
            + [pct(s["pass"][str(k)]) if str(k) in s["pass"] else "n/a" for k in range(1, 5)]
            + [num(s["violations"]), num(s["wrong_calls"], 2)]
        )
    return _table(head, rows)


def split_table(root: Path) -> list[str]:
    head = ["Agent", "Dev pass^1", "Dev pass^4", "Held-out pass^1", "Held-out pass^4"]
    rows = []
    for n in agents(root):
        g = load(root, n)["summary"]
        cells = []
        for split in ("dev", "heldout"):
            for k in ("1", "4"):
                cells.append(pct(g[split]["pass"][k]) if split in g and k in g[split]["pass"] else "n/a")
        rows.append([LABEL.get(n, f"`{n}`")] + cells)
    return _table(head, rows)


def domain_table(root: Path) -> list[str]:
    head = ["Agent"] + [f"{DOMAIN_LABEL[d]} pass^{k}" for d in DOMAIN_LABEL for k in (1, 4)]
    rows = []
    for n in agents(root):
        g = load(root, n)["summary"]
        rows.append(
            [LABEL.get(n, f"`{n}`")]
            + [
                pct(g[d]["pass"][k]) if d in g and k in g[d]["pass"] else "n/a"
                for d in DOMAIN_LABEL
                for k in ("1", "4")
            ]
        )
    return _table(head, rows)


def cost_table(root: Path) -> list[str]:
    head = ["Agent", "Tokens per task", "Turns per task", "Wall time for the run"]
    rows = []
    for n in agents(root):
        r = load(root, n)
        s, m = r["summary"]["all"], r["meta"]
        secs = f"{m['seconds']:.2f} s" if "seconds" in m else "n/a"
        rows.append([LABEL.get(n, f"`{n}`"), num(s["tokens"], 0), num(s["turns"]), secs])
    return _table(head, rows)


def record_text(root: Path) -> str:
    rec = json.loads((root / RECORD).read_text())
    if rec.get("status") != "ran":
        probes = ", ".join(f"{k} {v}" for k, v in sorted(rec.get("probe", {}).items()))
        seen = f" A probe of the provider hosts on that day gave: {probes}." if probes else ""
        return (
            f"Record mode did not run. Checked on {rec['date']} for model `{rec['model']}`: {rec['reason']}{seen} "
            "So no row on this page comes from a language model, and Done-means item 4 is open. "
            "The LLM agent in `src/deskbench/agents/llm.py` passes all 45 tasks against a fake local server "
            "in `tests/test_llm_agent.py`, so the loop, the tool calls, the JSON fallback, record and replay all run. "
            "`docs/HUMAN_STEPS.md` has the command to run once a free key exists."
        )
    m = rec
    done = f"{m['tasks_done']} of {m['tasks_asked']} tasks" + (
        f", stopped at {m['stopped']}" if m.get("stopped") else ""
    )
    return f"Record run of {m['date']}, model `{m['model']}`, seed {m['seed']}, {m['trials']} trials, {done}. File `{m['results']}`."


def blocks(root: Path) -> dict[str, str]:
    o, f = load(root, "oracle"), load(root, "flaky")
    sec = load(root, SECOND)
    om, fa = o["meta"], f["summary"]["all"]
    out = {
        "status": (
            f"**Status:** v{om['version'].replace('rc', '-rc')} release candidate. "
            f"{o['summary']['all']['tasks']} tasks in 3 domains, all passed by the oracle. "
            + (
                "No model run yet: record mode is blocked in this build (see Results)."
                if json.loads((root / RECORD).read_text()).get("status") != "ran"
                else "Includes a record-mode model run."
            )
        ),
        "results": "\n".join(
            [*(f"- {meta_line(load(root, n), n)}" for n in agents(root)), "", *main_table(root)]
        ),
        "splits": "\n".join(split_table(root)),
        "second": (
            f"The oracle scores {pct(o['summary']['all']['pass']['4'])} on pass^4, which looks too good. "
            "It is a script written against the policy, so it should. To rule out a lucky seed, it ran again on seeds "
            f"{sec['meta']['seed']} to {sec['meta']['seed'] + sec['meta']['trials'] - 1} "
            f"(file `results/{SECOND}.json`): pass^4 {pct(sec['summary']['all']['pass']['4'])}, "
            f"{sec['summary']['all']['violations'][0]:.1f} violations per 100 trials."
        ),
        "decay": (
            f"The flaky agent shows why pass^k matters. Its pass^1 is {pct(fa['pass']['1'])}, "
            f"but its pass^4 falls to {pct(fa['pass']['4'])}. One good chat in four tries hides that."
        ),
        "cost": "\n".join(
            [
                *cost_table(root),
                "",
                f"Scripted agents send no tokens, so their cost is zero. Times are for 180 trials on one core of "
                f"`{om['cpu']}` on {om['date']}.",
            ]
        ),
        "record": record_text(root),
        "qa_numbers": "\n".join(
            [
                f"From `results/flaky.json` (seed {f['meta']['seed']}): pass^1 {pct(fa['pass']['1'])}, "
                f"pass^4 {pct(fa['pass']['4'])}.",
                f"From `results/no-identity.json`: pass^1 {pct(load(root, 'no-identity')['summary']['all']['pass']['1'])}, "
                f"{load(root, 'no-identity')['summary']['all']['violations'][0]:.1f} violations per 100 trials.",
                f"From `results/no-windows.json`: pass^1 {pct(load(root, 'no-windows')['summary']['all']['pass']['1'])}.",
                f"From `results/oracle.json`: pass^4 {pct(o['summary']['all']['pass']['4'])}.",
            ]
        ),
    }
    return out


def failures(root: Path, name: str) -> list[str]:
    res = load(root, name)
    by: dict[str, list[dict]] = {}
    for t in res["trials"]:
        by.setdefault(t["task"], []).append(t)
    lines = []
    for task, ts in sorted(by.items()):
        bad = [t for t in ts if not t["passed"]]
        if not bad:
            continue
        rules = sorted({v["rule"] for t in bad for v in t["violations"]})
        why = ", ".join(rules) if rules else bad[0]["problems"][0]
        link = next(t["transcript_file"] for t in bad if "transcript_file" in t)
        lines.append(f"- `{task}` failed {len(bad)} of {len(ts)} trials: {why}. [Transcript](../{link})")
    return lines or ["- None."]


def report(root: Path) -> str:
    parts = [
        "# deskbench report",
        "",
        "`deskbench readme` writes this file from `results/`. Do not edit it by hand.",
        "",
        "pass^k is the chance that k trials of the same task all pass, estimated per task as C(c, k) / C(n, k) "
        "and averaged over tasks. Brackets hold a bootstrap 95% interval over tasks.",
        "",
        "## Runs",
        "",
        *(f"- {meta_line(load(root, n), n)}" for n in agents(root)),
        "",
        "## Results",
        "",
        *main_table(root),
        "",
        "## Dev and held-out tasks",
        "",
        *split_table(root),
        "",
        "## By domain",
        "",
        *domain_table(root),
        "",
        "## Cost",
        "",
        *cost_table(root),
        "",
        "## Record mode",
        "",
        record_text(root),
        "",
        "## Failures",
        "",
        "Each line names the rules that fired, or the first scoring problem when no rule fired. "
        "The link opens the first failed trial of that task.",
    ]
    for n in agents(root):
        parts += ["", f"### {LABEL.get(n, n)}", "", *failures(root, n)]
    return "\n".join(parts) + "\n"


def page(root: Path) -> str:
    def md_table(lines: list[str]) -> str:
        rows = [
            [c.strip().strip("`") for c in ln.strip("|").split("|")]
            for ln in lines
            if not ln.startswith("| ---")
        ]
        head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    runs = "".join(f"<li>{html.escape(meta_line(load(root, n), n))}</li>" for n in agents(root))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>deskbench results</title>
<style>
:root {{ --bg:#ffffff; --fg:#1b1f24; --muted:#57606a; --line:#d0d7de; --head:#f6f8fa; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#9aa4ae; --line:#30363d; --head:#161b22; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; margin:0 auto; max-width:1100px; padding:24px 16px; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0 28px; font-size:13px; display:block; overflow-x:auto; }}
th, td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; white-space:nowrap; }}
th {{ background:var(--head); }}
li, p.meta {{ color:var(--muted); }}
</style>
</head>
<body>
<h1 id="top">deskbench results</h1>
<p>Support agents on three invented small businesses, scored by the database state at the end of each chat.
pass^k is the chance that k trials of the same task all pass. Brackets hold a bootstrap 95% interval over tasks.</p>
<ul>{runs}</ul>
<h2 id="results">Results</h2>
{md_table(main_table(root))}
<h2 id="splits">Dev and held-out tasks</h2>
{md_table(split_table(root))}
<h2 id="domains">By domain</h2>
{md_table(domain_table(root))}
<h2 id="cost">Cost</h2>
{md_table(cost_table(root))}
<h2 id="record">Record mode</h2>
<p class="meta">{html.escape(record_text(root))}</p>
<p><a href="REPORT.md">Full report with failures</a> · <a href="../README.md">README</a></p>
</body>
</html>
"""


def write(root: Path, check: bool = False) -> list[str]:
    """Rewrite every block and page. With check, change nothing and return the files that are out of date."""
    b, stale = blocks(root), []
    for rel in FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text()
        new = BLOCK.sub(lambda m: m.group(1) + b[m.group(2)] + "\n" + m.group(4), text)
        if new != text:
            stale.append(rel)
            if not check:
                path.write_text(new)
    for rel, content in (("docs/REPORT.md", report(root)), ("docs/index.html", page(root))):
        path = root / rel
        if not path.exists() or path.read_text() != content:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
    return stale
