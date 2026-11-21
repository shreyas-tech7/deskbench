"""Domain shape: policy, database, tool count, task count and splits."""

import pytest

from deskbench.domains import DOMAINS
from deskbench.scorer import snapshot


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_domain_shape(name):
    d = DOMAINS[name]
    assert 6 <= len(d.tools) <= 10
    assert len(d.tasks) == 15
    assert len(d.policy_text.splitlines()) < 70  # one page
    assert sum(t["split"] == "heldout" for t in d.tasks) == 5
    ids = [t["id"] for t in d.tasks]
    assert len(set(ids)) == len(ids)
    snap = snapshot(d.fresh_db())
    assert sum(bool(rows) for rows in snap.values()) >= 3  # seeded, apart from log tables


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_tool_schemas_are_openai_shaped(name):
    for t in DOMAINS[name].tools.values():
        s = t.schema()
        assert s["type"] == "function" and s["function"]["name"] == t.name
        assert set(s["function"]["parameters"]["required"]) == set(t.params)


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_tasks_are_well_formed(name):
    d = DOMAINS[name]
    tables = set(snapshot(d.fresh_db()))
    for t in d.tasks:
        assert t["expected"]["outcome"] in ("resolved", "refused", "transferred")
        assert len(t["opening"]) >= 2 and t["nudge"]
        assert set(t["facts"]) <= set(d.fact_asks), t["id"]
        for spec in t["expected"]["db"]:
            assert spec["table"] in tables
            assert ("count" in spec) != ("fields" in spec)
        if "refusal" in t["tags"]:
            assert t["expected"]["outcome"] == "refused"
        if "transfer" in t["tags"]:
            assert t["expected"]["outcome"] == "transferred"


def test_each_domain_has_refusal_and_transfer_tasks():
    for d in DOMAINS.values():
        outcomes = {t["expected"]["outcome"] for t in d.tasks}
        assert outcomes == {"resolved", "refused", "transferred"}, d.name
