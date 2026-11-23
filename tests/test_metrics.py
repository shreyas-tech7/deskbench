import pytest

from deskbench.metrics import by_task, interval, pass_hat_k, summarize, summarize_groups


def _t(task, passed, split="dev", domain="bikeparts", v=0, wrong=0, turns=4, tokens=0):
    return {
        "task": task,
        "passed": passed,
        "split": split,
        "domain": domain,
        "violations": [{"rule": "X"}] * v,
        "wrong_calls": wrong,
        "turns": turns,
        "tokens": tokens,
    }


@pytest.mark.parametrize(
    "c,n,k,want",
    [
        (4, 4, 4, 1.0),
        (3, 4, 1, 0.75),
        (3, 4, 2, 0.5),
        (3, 4, 3, 0.25),
        (3, 4, 4, 0.0),
        (2, 4, 2, 1 / 6),
        (0, 4, 1, 0.0),
    ],
)
def test_pass_hat_k_by_hand(c, n, k, want):
    assert pass_hat_k(c, n, k) == pytest.approx(want)


def test_pass_hat_k_needs_enough_trials():
    with pytest.raises(ValueError):
        pass_hat_k(1, 2, 3)


def test_summary_averages_over_tasks():
    # Task a passes 4 of 4, task b passes 2 of 4. pass^2 = (1 + 1/6) / 2.
    trials = [_t("a", True)] * 4 + [_t("b", i < 2, v=1, wrong=2, tokens=100) for i in range(4)]
    s = summarize(trials, boot=200)
    assert s["tasks"] == 2 and s["trials_per_task"] == 4
    assert s["pass"][1][0] == pytest.approx(0.75)
    assert s["pass"][2][0] == pytest.approx((1 + 1 / 6) / 2)
    assert s["pass"][4][0] == pytest.approx(0.5)
    assert s["violations"][0] == pytest.approx(50.0)  # per 100 trials: task a 0, task b 100
    assert s["wrong_calls"][0] == pytest.approx(1.0)
    assert s["tokens"][0] == pytest.approx(50.0)


def test_interval_holds_the_mean_and_is_seeded():
    vals = [0, 0, 1, 1, 1, 0.5, 0.25, 1, 0, 1]
    mean, lo, hi = interval(vals)
    assert lo <= mean <= hi and 0 <= lo and hi <= 1
    assert interval(vals) == interval(vals)
    assert interval([1.0] * 5) == (1.0, 1.0, 1.0)


def test_k_beyond_trials_is_left_out():
    s = summarize([_t("a", True), _t("a", False)], boot=50)
    assert set(s["pass"]) == {1, 2}


def test_groups_split_dev_heldout_and_domain():
    trials = [_t("a", True), _t("b", False, split="heldout", domain="salon")]
    g = summarize_groups(trials, boot=50)
    assert set(g) == {"all", "dev", "heldout", "bikeparts", "salon"}
    assert g["heldout"]["pass"][1][0] == 0.0
    assert list(by_task(trials)) == ["a", "b"]
