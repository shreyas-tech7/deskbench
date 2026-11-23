"""An LLM agent over any OpenAI-compatible chat API, with record and replay of every request.

Keys come only from environment variables. Tests run it against a fake server on 127.0.0.1.
Replay reads saved responses keyed by a hash of the request, so a recorded run repeats offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..episode import Call, Say

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.1-8b-instant"),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
}
ACTION = re.compile(r"\{.*\}", re.S)


class MissingFixture(KeyError):
    pass


def request_key(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


class HttpClient:
    def __init__(
        self, base_url: str, key: str, model: str, timeout: float = 90, retries: int = 5, wait: float = 2.0
    ):
        if not re.match(r"^(https://|http://127\.0\.0\.1[:/])", base_url):
            raise ValueError("base_url must be https, or http on 127.0.0.1 for tests")
        self.base_url, self.key, self.model = base_url.rstrip("/"), key, model
        self.timeout, self.retries, self.wait = timeout, retries, wait

    def complete(self, body: dict) -> dict:
        data = json.dumps(body).encode()
        wait = self.wait
        for attempt in range(self.retries):
            req = urllib.request.Request(  # noqa: S310 (scheme checked in __init__)
                self.base_url + "/chat/completions",
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 (https or 127.0.0.1 only)
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == self.retries - 1:
                    raise
                time.sleep(wait)
                wait *= 2
        raise RuntimeError("unreachable")


class RecordClient:
    """Saves each response as fixtures/<model>/<hash>.json, and reuses a saved one, so a stopped run resumes."""

    def __init__(self, inner, folder: Path):
        self.inner, self.model = inner, inner.model
        self.folder = Path(folder) / re.sub(r"[^\w.-]", "_", self.model)
        self.folder.mkdir(parents=True, exist_ok=True)

    def complete(self, body: dict) -> dict:
        path = self.folder / f"{request_key(body)}.json"
        if path.exists():
            return json.loads(path.read_text())
        out = self.inner.complete(body)
        path.write_text(json.dumps(out, indent=1, sort_keys=True))
        return out


class ReplayClient:
    """Answers only from saved fixtures. A request that was never recorded is an error, not a live call."""

    def __init__(self, folder: Path, model: str):
        self.model = model
        self.folder = Path(folder) / re.sub(r"[^\w.-]", "_", model)

    def complete(self, body: dict) -> dict:
        path = self.folder / f"{request_key(body)}.json"
        if not path.exists():
            raise MissingFixture(f"no fixture {path.name} for this request")
        return json.loads(path.read_text())


def from_env(provider: str) -> HttpClient | None:
    base, var, model = PROVIDERS[provider]
    key = os.environ.get(var)
    return HttpClient(base, key, model) if key else None


def system_prompt(domain) -> str:
    return (
        f"You are the customer support agent for {domain.business}. The time now is "
        f"{domain.now:%Y-%m-%d %H:%M}. Follow this policy exactly.\n\n{domain.policy_text}\n\n"
        "Use the tools to read and change records. Talk to the customer in plain sentences. "
        "End every chat with close_ticket or transfer_to_human. If you cannot call tools natively, "
        'reply with only a JSON object like {"tool": "find_customer", "args": {"email": "a@b.test"}}.'
    )


def parse_action(text: str) -> Call | None:
    """The fallback for models without native tool calls: a JSON object with tool and args."""
    m = ACTION.search(text or "")
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
        args = obj.get("args", obj.get("arguments", {}))
        return Call(obj["tool"], args if isinstance(args, dict) else {})
    return None


class LLMAgent:
    def __init__(self, client, name: str | None = None, max_tokens: int = 400):
        self.client, self.max_tokens = client, max_tokens
        self.name = name or f"llm:{client.model}"

    def reset(self, domain, seed):
        self.domain, self.seed, self.tokens = domain, seed, 0
        self.tools = [t.schema() for t in domain.tools.values()]
        self.messages = [{"role": "system", "content": system_prompt(domain)}]
        self.queue: list[tuple[str | None, Call]] = []
        self.pending: tuple[str | None, str] | None = None  # the call whose result comes next

    def act(self, obs):
        if obs[0] == "user":
            self.messages.append({"role": "user", "content": obs[1]})
        else:
            call_id, name = self.pending
            content = json.dumps(obs[2], sort_keys=True)
            if call_id:
                self.messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
            else:
                self.messages.append({"role": "user", "content": f"Result of {name}: {content}"})
        if not self.queue:
            self._ask()
        call_id, action = self.queue.pop(0)
        if isinstance(action, Call):
            self.pending = (call_id, action.name)
        return action

    def _ask(self):
        body = {
            "model": self.client.model,
            "messages": self.messages,
            "tools": self.tools,
            "temperature": 0,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }
        out = self.client.complete(json.loads(json.dumps(body)))
        self.tokens += int((out.get("usage") or {}).get("total_tokens", 0))
        msg = out["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if calls:
            self.messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
            for c in calls:
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                self.queue.append(
                    (c["id"], Call(c["function"]["name"], args if isinstance(args, dict) else {}))
                )
            return
        text = (msg.get("content") or "").strip()
        self.messages.append({"role": "assistant", "content": text})
        action = parse_action(text)
        self.queue.append(
            (None, action) if action else (None, Say(text or "Sorry, could you say that again?"))
        )
