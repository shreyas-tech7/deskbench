import pytest
from fake_llm import FakeServer, OracleBrain

from deskbench.agents.llm import (
    HttpClient,
    LLMAgent,
    MissingFixture,
    RecordClient,
    ReplayClient,
    parse_action,
)
from deskbench.domains import DOMAINS, all_tasks
from deskbench.episode import Call, run_trial, transcript_bytes


def _run(domain, task, seed, **brain):
    with FakeServer(OracleBrain(domain, seed, **brain)) as srv:
        agent = LLMAgent(HttpClient(srv.url, "test-key", "fake-model", wait=0.01))
        return run_trial(domain, task, agent, seed), srv


@pytest.mark.parametrize("domain,task", all_tasks(), ids=lambda x: getattr(x, "name", None) or x["id"])
def test_llm_loop_over_http_passes_with_an_oracle_brain(domain, task):
    trial, _ = _run(domain, task, 1)
    assert trial["passed"], trial["problems"]
    assert trial["tokens"] > 0


def test_json_action_fallback_works_end_to_end():
    d = DOMAINS["bikeparts"]
    trial, _ = _run(d, d.task("bk01"), 3, json_mode=True)
    assert trial["passed"], trial["problems"]


def test_rate_limit_is_retried():
    d = DOMAINS["salon"]
    trial, srv = _run(d, d.task("sl01"), 1, fail_first=2)
    assert trial["passed"]
    assert len(srv.requests) == srv.brain.n + 2


def test_requests_send_tools_policy_and_seed():
    d = DOMAINS["mealkit"]
    _, srv = _run(d, d.task("mk05"), 4)
    body = srv.requests[0]
    assert body["temperature"] == 0 and body["seed"] == 4
    assert {t["function"]["name"] for t in body["tools"]} == set(d.tools)
    assert d.policy_text.splitlines()[0] in body["messages"][0]["content"]


def test_record_then_replay_gives_the_same_transcript(tmp_path):
    d = DOMAINS["bikeparts"]
    task = d.task("bk05")
    with FakeServer(OracleBrain(d, 2)) as srv:
        rec = LLMAgent(RecordClient(HttpClient(srv.url, "k", "fake/model:free"), tmp_path))
        first = run_trial(d, task, rec, 2)
    replay = LLMAgent(ReplayClient(tmp_path, "fake/model:free"))
    second = run_trial(d, task, replay, 2)
    assert transcript_bytes(first) == transcript_bytes(second)
    assert first["tokens"] == second["tokens"]
    assert list(tmp_path.iterdir())[0].name == "fake_model_free"


def test_replay_never_goes_live_on_a_missing_fixture(tmp_path):
    d = DOMAINS["salon"]
    with pytest.raises(MissingFixture):
        run_trial(d, d.task("sl01"), LLMAgent(ReplayClient(tmp_path, "m")), 1)


def test_client_refuses_plain_http_to_other_hosts():
    with pytest.raises(ValueError):
        HttpClient("http://example.test/v1", "k", "m")


@pytest.mark.parametrize(
    "text,want",
    [
        ('{"tool": "get_order", "args": {"order_id": 1001}}', Call("get_order", {"order_id": 1001})),
        ('Sure. {"tool": "list_plans", "arguments": {}}', Call("list_plans", {})),
        ("Hello, how can I help?", None),
        ('{"not": "a call"}', None),
        ("{broken json", None),
    ],
)
def test_parse_action(text, want):
    assert parse_action(text) == want


def test_record_resumes_from_saved_fixtures(tmp_path):
    d = DOMAINS["salon"]
    task = d.task("sl04")
    with FakeServer(OracleBrain(d, 5)) as srv:
        run_trial(d, task, LLMAgent(RecordClient(HttpClient(srv.url, "k", "m"), tmp_path)), 5)
        first = len(srv.requests)
        run_trial(d, task, LLMAgent(RecordClient(HttpClient(srv.url, "k", "m"), tmp_path)), 5)
    assert first > 0 and len(srv.requests) == first
