"""Run one trial: fresh database copy, scripted user, agent, dispatcher, then score the end state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .core import Domain
from .dispatcher import Dispatcher
from .scorer import score, snapshot
from .user import ScriptedUser


@dataclass
class Say:
    text: str


@dataclass
class Call:
    name: str
    args: dict = field(default_factory=dict)


MAX_STEPS = 60  # agent actions per trial, a guard against loops


def run_trial(domain: Domain, task: dict, agent, seed: int, max_turns: int = 20) -> dict:
    db = domain.fresh_db()
    before = snapshot(db)
    disp = Dispatcher(domain, db)
    user = ScriptedUser(domain, task, seed, max_turns)
    agent.reset(domain, seed)
    text = user.open()
    transcript = [{"role": "user", "text": text}]
    last_user, obs, steps = text, ("user", text), 0
    while not user.done and steps < MAX_STEPS:
        steps += 1
        action = agent.act(obs)
        if isinstance(action, Call):
            result = disp.call(action.name, action.args, last_user)
            transcript.append({"role": "call", "tool": action.name, "args": action.args, "result": result})
            obs = ("tool", action.name, result)
            if disp.ended:
                user.reply("", ended=True)
            continue
        transcript.append({"role": "agent", "text": action.text})
        reply = user.reply(action.text, ended=bool(disp.ended))
        if reply is None:
            break
        transcript.append({"role": "user", "text": reply})
        last_user, obs = reply, ("user", reply)
    result = score(task, before, db, disp.violations)
    return {
        "task": task["id"],
        "domain": domain.name,
        "split": task["split"],
        "tags": task["tags"],
        "seed": seed,
        "agent": agent.name,
        **result,
        "violations": disp.violations,
        "wrong_calls": disp.wrong_calls,
        "tool_calls": len(disp.log),
        "turns": sum(1 for m in transcript if m["role"] in ("user", "agent")),
        "tokens": getattr(agent, "tokens", 0),
        "transcript": transcript,
    }


def transcript_bytes(trial: dict) -> bytes:
    return json.dumps(trial["transcript"], sort_keys=True, ensure_ascii=False).encode()
