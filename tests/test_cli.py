import json

import pytest
from fake_llm import FakeServer, OracleBrain

from deskbench import cli
from deskbench.domains import DOMAINS


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    return tmp_path


def test_run_writes_results_and_failed_transcripts(root, capsys):
    assert cli.main(["run", "no-windows", "--trials", "2", "--seed", "7"]) == 0
    res = json.loads((root / "results" / "no-windows.json").read_text())
    assert res["meta"]["seed"] == 7 and res["meta"]["trials"] == 2
    assert len(res["trials"]) == 90
    failed = [t for t in res["trials"] if "transcript_file" in t]
    assert failed and all((root / t["transcript_file"]).exists() for t in failed)
    assert "pass^2=" in capsys.readouterr().out


def test_show_prints_a_passing_chat(root, capsys):
    assert cli.main(["show", "sl02"]) == 0
    out = capsys.readouterr().out
    assert "[tool] cancel_booking" in out and "result: PASS" in out


def test_determinism_command(root, capsys):
    assert cli.main(["determinism", "--seed", "3"]) == 0
    assert "45 of 45" in capsys.readouterr().out


def test_record_without_a_key_is_blocked_and_says_so(root, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert cli.main(["llm", "--mode", "record"]) == 2
    status = json.loads((root / "results" / "record-status.json").read_text())
    assert status["status"] == "blocked" and "GROQ_API_KEY" in status["reason"]


def test_record_then_replay_through_the_cli(root, monkeypatch):
    """Record two tasks against a fake endpoint, then replay them with no server at all."""
    monkeypatch.setenv("FAKE_KEY", "k")

    class PerTrial(OracleBrain):  # a fresh oracle per trial, keyed by the system prompt and first user line
        def __init__(self):
            self.json_mode, self.fail_left, self.n, self.brains = False, 0, 0, {}

        def answer(self, body):
            key = (body["seed"], body["messages"][1]["content"])
            if key not in self.brains:
                domain = next(x for x in DOMAINS.values() if x.business in body["messages"][0]["content"])
                self.brains[key] = OracleBrain(domain, body["seed"])
            return self.brains[key].answer(body)

    with FakeServer(PerTrial()) as srv:
        args = [
            "llm",
            "--base-url",
            srv.url,
            "--model",
            "fake-1",
            "--key-env",
            "FAKE_KEY",
            "--limit",
            "2",
            "--trials",
            "2",
        ]
        assert cli.main([*args, "--mode", "record"]) == 0
    rec = json.loads((root / "results" / "llm-fake-1.json").read_text())
    assert rec["summary"]["all"]["pass"]["1"][0] == 1.0 and rec["meta"]["tasks_done"] == 2
    status = json.loads((root / "results" / "record-status.json").read_text())
    assert status["status"] == "ran"
    assert cli.main([*args, "--mode", "replay"]) == 0
    rep = json.loads((root / "results" / "llm-fake-1.json").read_text())
    assert rep["summary"] == rec["summary"]


def test_replay_with_no_fixtures_stops_cleanly(root, capsys):
    assert cli.main(["llm", "--mode", "replay", "--limit", "1", "--trials", "1"]) == 1
    assert "stopped after 0 of 1" in capsys.readouterr().err
