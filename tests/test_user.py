"""Scripted user: every transition in the table, facts hidden until asked, byte-identical replays."""

import pytest

from deskbench import user as U
from deskbench.agents.oracle import oracle_for
from deskbench.domains import DOMAINS, all_tasks
from deskbench.episode import run_trial, transcript_bytes

D = DOMAINS["bikeparts"]
TASK = D.task("bk01")


def _talking(seed=1):
    u = U.ScriptedUser(D, TASK, seed)
    u.open()
    return u


def test_open_moves_start_to_talking():
    u = U.ScriptedUser(D, TASK, 1)
    assert u.state == U.START
    assert u.open() in TASK["opening"] and u.state == U.TALKING


@pytest.mark.parametrize(
    "agent_text,ended,event",
    [
        ("", True, U.ENDED),
        ("What is the email on your account?", False, U.ASKS_FACT),
        ("I can return it. Shall I go ahead?", False, U.ASKS_CONFIRM),
        ("Done. Is there anything else I can help with?", False, U.ASKS_MORE),
        ("Let me look into that.", False, U.OTHER),
    ],
)
def test_classify(agent_text, ended, event):
    assert _talking().classify(agent_text, ended)[0] == event


def test_every_transition_in_the_table():
    for (state, event), (nxt, action) in U.TRANSITIONS.items():
        u = U.ScriptedUser(D, TASK, 1)
        u.state = state
        out = u.step(event, ["email"])
        assert u.state == nxt, (state, event)
        assert (out is None) == (action == "stop")


def test_facts_stay_hidden_until_asked():
    """Broken case: a user that volunteers facts would make the identity questions free."""
    u = U.ScriptedUser(D, TASK, 1)
    opening = u.open()
    for value in TASK["facts"].values():
        assert value not in opening
    reply = u.reply("What is the email on your account?")
    assert TASK["facts"]["email"] in reply and TASK["facts"]["zip"] not in reply
    assert u.revealed == ["email"]


def test_unknown_fact_is_admitted():
    u = U.ScriptedUser(D, D.task("bk13"), 1)
    u.open()
    assert "don't" in u.reply("What is the order number?")


def test_yes_only_when_asked_to_confirm():
    u = _talking()
    assert u.reply("Shall I go ahead?").startswith("Yes")
    assert not u.reply("Let me check.").startswith("Yes")


def test_user_gives_up_after_three_nudges():
    u = _talking()
    for _ in range(U.MAX_NUDGES):
        assert u.reply("Hmm.") == TASK["nudge"]
    assert u.reply("Hmm.") == U.GIVE_UP and u.done


def test_turn_limit_ends_the_chat():
    u = U.ScriptedUser(D, TASK, 1, max_turns=2)
    u.open()
    u.reply("What is the email on your account?")
    assert u.reply("What is the zip code?") == U.GIVE_UP and u.done


@pytest.mark.parametrize("domain,task", all_tasks(), ids=[t["id"] for _, t in all_tasks()])
def test_same_seed_gives_byte_identical_transcripts(domain, task):
    """Done-means item 5."""
    a = run_trial(domain, task, oracle_for(domain.name), 7)
    b = run_trial(domain, task, oracle_for(domain.name), 7)
    assert transcript_bytes(a) == transcript_bytes(b)


def test_different_seeds_change_the_words():
    texts = {transcript_bytes(run_trial(D, TASK, oracle_for("bikeparts"), s)) for s in range(6)}
    assert len(texts) > 1
