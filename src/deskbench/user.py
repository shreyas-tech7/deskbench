"""The scripted customer. A small state machine that hides each fact until the agent asks for it.

The same task and seed always give the same words, so transcripts replay byte for byte.
"""

from __future__ import annotations

import random

from .core import Domain

START, TALKING, DONE = "start", "talking", "done"
# Events, from the agent's side of the chat.
OPEN, ENDED, ASKS_FACT, ASKS_CONFIRM, ASKS_MORE, OTHER, STALLED, TURN_LIMIT = (
    "open",
    "ended",
    "asks_fact",
    "asks_confirm",
    "asks_more",
    "other",
    "stalled",
    "turn_limit",
)
# (state, event) -> (next state, what the user does). Every pair the machine can meet is listed.
TRANSITIONS = {
    (START, OPEN): (TALKING, "say_opening"),
    (TALKING, ENDED): (DONE, "stop"),
    (TALKING, TURN_LIMIT): (DONE, "give_up"),
    (TALKING, ASKS_FACT): (TALKING, "give_facts"),
    (TALKING, ASKS_CONFIRM): (TALKING, "say_yes"),
    (TALKING, ASKS_MORE): (TALKING, "say_no_more"),
    (TALKING, OTHER): (TALKING, "nudge"),
    (TALKING, STALLED): (DONE, "give_up"),
}
CONFIRM_ASKS = [
    "shall i",
    "should i",
    "would you like me to",
    "do you want me to",
    "can i go ahead",
    "confirm",
]
MORE_ASKS = ["anything else"]
MAX_NUDGES = 3

ANSWER = ["My {label} is {value}.", "It's {value}.", "Sure, my {label} is {value}."]
UNKNOWN = ["Sorry, I don't have my {label} handy.", "I don't know my {label}, sorry."]
YES = ["Yes, please go ahead.", "Yes, please do that.", "Yes, that's right, go ahead."]
NO_MORE = ["No, that's all. Thanks!", "No, that's everything.", "Nope, that's it, thank you."]
GIVE_UP = "I'll try again later. Bye."


class ScriptedUser:
    def __init__(self, domain: Domain, task: dict, seed: int, max_turns: int = 20):
        self.domain, self.task = domain, task
        self.rng = random.Random(f"{task['id']}:{seed}")  # noqa: S311 (seeded for replay, not security)
        self.state, self.turns, self.nudges, self.max_turns = START, 0, 0, max_turns
        self.revealed: list[str] = []

    def classify(self, agent_text: str, ended: bool) -> tuple[str, list[str]]:
        if ended:
            return ENDED, []
        if self.turns >= self.max_turns:
            return TURN_LIMIT, []
        low = agent_text.lower()
        asked = [k for k, pats in self.domain.fact_asks.items() if any(p in low for p in pats)]
        if asked:
            return ASKS_FACT, asked
        if any(p in low for p in CONFIRM_ASKS):
            return ASKS_CONFIRM, []
        if any(p in low for p in MORE_ASKS):
            return ASKS_MORE, []
        return (STALLED if self.nudges >= MAX_NUDGES else OTHER), []

    def step(self, event: str, asked: list[str] | None = None) -> str | None:
        self.state, action = TRANSITIONS[(self.state, event)]
        self.turns += 1
        if event != OTHER:
            self.nudges = 0
        return getattr(self, "_" + action)(asked or [])

    def open(self) -> str:
        return self.step(OPEN)

    def reply(self, agent_text: str, ended: bool = False) -> str | None:
        """The user's answer, or None once the chat is over."""
        return self.step(*self.classify(agent_text, ended))

    @property
    def done(self) -> bool:
        return self.state == DONE

    def _say_opening(self, _):
        return self.rng.choice(self.task["opening"])

    def _give_facts(self, asked):
        out = []
        for key in asked:
            label = self.domain.fact_labels[key]
            if key in self.task["facts"]:
                forms = self.domain.fact_templates.get(key, ANSWER)
                out.append(self.rng.choice(forms).format(label=label, value=self.task["facts"][key]))
                self.revealed.append(key)
            else:
                out.append(self.rng.choice(UNKNOWN).format(label=label))
        return " ".join(out)

    def _say_yes(self, _):
        return self.rng.choice(YES)

    def _say_no_more(self, _):
        return self.rng.choice(NO_MORE)

    def _nudge(self, _):
        self.nudges += 1
        return self.task["nudge"]

    def _give_up(self, _):
        return GIVE_UP

    def _stop(self, _):
        return None
