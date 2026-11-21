"""Done-means item 2, first half: the oracle solves every task. Wrong or impossible tasks fail here."""

import pytest

from deskbench.agents.oracle import oracle_for
from deskbench.domains import all_tasks
from deskbench.episode import run_trial

TASKS = all_tasks()


@pytest.mark.parametrize("domain,task", TASKS, ids=[t["id"] for _, t in TASKS])
@pytest.mark.parametrize("seed", [1, 2])
def test_oracle_passes(domain, task, seed):
    r = run_trial(domain, task, oracle_for(domain.name), seed)
    assert r["passed"], r["problems"]
    assert r["wrong_calls"] == 0


def test_task_count():
    from deskbench.domains import DOMAINS

    assert sum(len(d.tasks) for d in DOMAINS.values()) == 15 * len(DOMAINS)
