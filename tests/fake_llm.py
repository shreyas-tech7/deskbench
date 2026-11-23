"""A fake OpenAI-compatible server on 127.0.0.1 for the LLM agent tests.

Its brain is the scripted oracle: each request's last message is turned back into an
observation, the oracle picks the action, and the server sends it as a tool call or text.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from deskbench.agents.oracle import oracle_for
from deskbench.episode import Call


class OracleBrain:
    def __init__(self, domain, seed, json_mode=False, fail_first=0):
        self.oracle = oracle_for(domain.name)
        self.oracle.reset(domain, seed)
        self.json_mode, self.fail_left, self.n = json_mode, fail_first, 0

    def answer(self, body):
        msgs = body["messages"]
        last = msgs[-1]
        if last["role"] == "tool":
            name = next(
                c["function"]["name"]
                for m in msgs
                if m.get("tool_calls")
                for c in m["tool_calls"]
                if c["id"] == last["tool_call_id"]
            )
            obs = ("tool", name, json.loads(last["content"]))
        elif last["content"].startswith("Result of "):
            name, _, rest = last["content"][len("Result of ") :].partition(": ")
            obs = ("tool", name, json.loads(rest))
        else:
            obs = ("user", last["content"])
        action = self.oracle.act(obs)
        self.n += 1
        usage = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}
        if isinstance(action, Call):
            if self.json_mode:
                msg = {"role": "assistant", "content": json.dumps({"tool": action.name, "args": action.args})}
            else:
                fn = {"name": action.name, "arguments": json.dumps(action.args)}
                msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": f"c{self.n}", "type": "function", "function": fn}],
                }
        else:
            msg = {"role": "assistant", "content": action.text}
        return {"choices": [{"message": msg}], "usage": usage}


class FakeServer:
    def __init__(self, brain):
        self.brain, self.requests = brain, []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                if outer.brain.fail_left:
                    outer.brain.fail_left -= 1
                    self.send_response(429)
                    self.end_headers()
                    return
                data = json.dumps(outer.brain.answer(body)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()
