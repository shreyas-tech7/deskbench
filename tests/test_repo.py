"""Repo quality bar: README parts in order, generated numbers in sync, writing rules, shipped files."""

import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from deskbench.bench import BUILD_SEEDS, SCRIPTED
from deskbench.readme import RECORD, SECOND, write

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"```.*?```", re.S)
CODE = re.compile(r"`[^`]*`")
GEN = re.compile(r"<!-- gen:(\w+) -->.*?<!-- /gen:\1 -->", re.S)
SECTIONS = [
    "## The problem",
    "## How it works",
    "## Results",
    "## Cost per task",
    "## Run it in 10 minutes",
    "## Limits",
    "## Glossary",
    "## Related work",
    "## How this was built",
]


def test_readme_parts_in_order():
    text = (ROOT / "README.md").read_text()
    status = text.index("**Status:**")
    pos = [text.index(s) for s in SECTIONS]
    assert status < pos[0] and pos == sorted(pos)
    assert "```mermaid" in text and "badge.svg" in text
    assert "C(c, k) / C(n, k)" in text
    assert "docs/build/BUILD_PROMPT.md" in text and "not done yet" in text


def test_generated_files_match_results():
    """Broken case: someone types a number into the README or the QA page by hand."""
    assert write(ROOT, check=True) == []
    res = json.loads((ROOT / "results" / "flaky.json").read_text())
    p4 = res["summary"]["all"]["pass"]["4"]
    line = f"{100 * p4[0]:.1f}% ({100 * p4[1]:.1f} to {100 * p4[2]:.1f})"
    assert line in (ROOT / "README.md").read_text()
    assert line in (ROOT / "docs" / "INTERVIEW_QA.md").read_text()


def test_no_percent_outside_generated_blocks():
    """Broken case: a result typed into the prose. Only the interval name says 95%."""
    for rel in ("README.md", "docs/INTERVIEW_QA.md", "docs/WALKTHROUGH.md"):
        text = GEN.sub("", FENCE.sub("", (ROOT / rel).read_text()))
        found = set(re.findall(r"\d+(?:\.\d+)?%", text))
        assert found <= {"95%"}, (rel, found)
        assert not re.search(r"\d+ percent", text)


@pytest.mark.parametrize("name", [*SCRIPTED, SECOND])
def test_results_meet_the_brief(name):
    """Done-means items 2 and 4: every task, 4 trials, intervals in order, seeds unused while building."""
    res = json.loads((ROOT / "results" / f"{name}.json").read_text())
    m, s = res["meta"], res["summary"]
    assert m["seed"] not in BUILD_SEEDS and m["trials"] == 4
    assert s["all"]["tasks"] == 45 and s["dev"]["tasks"] == 30 and s["heldout"]["tasks"] == 15
    assert len(res["trials"]) == 180
    for k in ("1", "2", "3", "4"):
        mean, lo, hi = s["all"]["pass"][k]
        assert lo <= mean <= hi
    if name.startswith("oracle"):
        assert s["all"]["pass"]["4"][0] == 1.0


def test_record_mode_status_is_reported():
    """Done-means item 4: a record run, or the README says it could not run."""
    rec = json.loads((ROOT / RECORD).read_text())
    text = (ROOT / "README.md").read_text()
    if rec["status"] == "ran":
        assert rec["model"] in text
    else:
        assert "Record mode did not run" in text and rec["date"] in text


def _prose(path: Path) -> str:
    return CODE.sub("", FENCE.sub("", path.read_text(encoding="utf-8")))


DOCS = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "docs" / "handoff" / "COWORK_PROMPT.md"] + [
    p for p in sorted((ROOT / "docs").glob("*.md")) if p.name not in {"DEMO.md", "PLAN.md"}
]


@pytest.mark.parametrize("path", [p for p in DOCS if p.exists()], ids=lambda p: p.name)
def test_writing_rules(path):
    text = _prose(path)
    assert "—" not in text and "–" not in text, "no em or en dashes"
    assert " - " not in re.sub(r"\n\s*- ", "\n", text), "no dashes as punctuation"
    for line in text.splitlines():
        if not line.startswith("|"):
            assert ";" not in line, f"semicolon in prose: {line}"
    for bad in ("it is important to note", "testament", "pivotal", "seamless", "delve", "not just"):
        assert bad not in text.lower()


def test_ship_files():
    for f in [
        "LICENSE",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        ".env.example",
        ".pre-commit-config.yaml",
        ".github/workflows/ci.yml",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        "docs/index.html",
        "docs/REPORT.md",
        "docs/DEMO.md",
        "docs/ADD_A_DOMAIN.md",
        "docs/topics.txt",
        "docs/GITHUB_ABOUT.md",
        "docs/build/BUILD_PROMPT.md",
    ]:
        assert (ROOT / f).is_file(), f
    assert "Copyright (c) 2026 Shreyas" in (ROOT / "LICENSE").read_text()


def test_social_preview_size():
    head = (ROOT / "docs" / "social-preview.png").read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", head[16:24]) == (1280, 640)


def test_topics():
    topics = (ROOT / "docs" / "topics.txt").read_text().split()
    assert 5 <= len(topics) <= 20
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,24}", t) for t in topics)


def test_ci_workflow_follows_the_rules():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    for need in (
        "workflow_dispatch",
        "cancel-in-progress: true",
        "timeout-minutes: 5",
        '"3.11"',
        "./init.sh",
    ):
        assert need in ci, need


def test_link_check_passes():
    r = subprocess.run(  # noqa: S603 (fixed argv, our own script)
        [sys.executable, str(ROOT / "scripts" / "check_links.py")], capture_output=True, text=True, timeout=60
    )
    assert r.returncode == 0, r.stdout
