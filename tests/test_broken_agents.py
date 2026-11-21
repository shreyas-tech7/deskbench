"""Done-means item 2, second half: broken agents fail exactly the tasks they should. This proves the scorer."""

import pytest

from deskbench.agents.oracle import oracle_for
from deskbench.domains import all_tasks
from deskbench.episode import run_trial

TASKS = all_tasks()


def _failed(**flags):
    return {t["id"] for d, t in TASKS if not run_trial(d, t, oracle_for(d.name, **flags), 1)["passed"]}


def test_skipping_the_identity_check_fails_every_account_task():
    """Broken case: the agent looks the customer up but never verifies them."""
    assert _failed(skip_identity=True) == {t["id"] for _, t in TASKS if "identity" in t["tags"]}


def test_ignoring_time_windows_fails_every_window_task():
    """Broken case: the agent never checks refund, cancel or cutoff windows."""
    expected = {t["id"] for _, t in TASKS if "window" in t["tags"]}
    assert expected and _failed(ignore_windows=True) == expected


def test_skipping_confirmation_fails_every_write_task():
    """Broken case: the agent changes data without asking for a yes."""
    expected = {t["id"] for _, t in TASKS if "write" in t["tags"]}
    assert expected and _failed(skip_confirm=1.0) == expected


@pytest.mark.parametrize("flags", [{"skip_identity": True}, {"ignore_windows": True}, {"skip_confirm": 1.0}])
def test_broken_agents_pass_the_rest(flags):
    """The broken agents still pass tasks their bug cannot touch, so a failure is not just noise."""
    assert len(_failed(**flags)) < len(TASKS)
