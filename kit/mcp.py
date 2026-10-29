"""Client for Figma desktop's local MCP server (Dev Mode MCP). Used for dev handoff; doctor only checks it answers.

Every call has a hard deadline: the server sends SSE heartbeats, so a socket timeout alone never fires on a hung call."""
import json
import time
import urllib.request

from . import VERSION

URL = "http://127.0.0.1:3845/mcp"


class Client:
    def __init__(self, url=URL, timeout=240):
        self.url, self.sid, self.n, self.timeout = url, None, 0, timeout
        self.call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "figma-offline-kit", "version": VERSION}})
        self.call("notifications/initialized", notify=True)

    def call(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            self.n += 1
            body["id"] = self.n
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["mcp-session-id"] = self.sid
        r = urllib.request.urlopen(urllib.request.Request(self.url, json.dumps(body).encode(), h), timeout=self.timeout)
        self.sid = self.sid or r.headers.get("mcp-session-id")
        if notify:
            r.read()
            return None
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            buf, deadline = "", time.monotonic() + self.timeout
            while True:
                if time.monotonic() > deadline:
                    r.close()
                    raise TimeoutError(f"no response within {self.timeout}s")
                line = r.readline()
                if not line:
                    break
                line = line.decode("utf-8", "replace").rstrip("\r\n")
                if line.startswith("data:"):
                    buf += line[5:].lstrip()
                elif line == "" and buf:
                    msg, buf = json.loads(buf), ""
                    if msg.get("id") == body["id"]:
                        return msg
            return json.loads(buf) if buf else None
        return json.loads(r.read().decode("utf-8"))

    def tools(self):
        res = self.call("tools/list") or {}
        return [t.get("name") for t in res.get("result", {}).get("tools", [])]

    def tool(self, name, **args):
        res = self.call("tools/call", {"name": name, "arguments": args})
        if res is None:
            raise RuntimeError("no response")
        if "error" in res:
            raise RuntimeError(str(res["error"])[:300])
        return res["result"]


def text_of(result):
    return "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


def probe(timeout=4):
    """(True, [tool names]) if the desktop MCP answers, else (False, reason)."""
    try:
        c = Client(timeout=timeout)
        return True, c.tools()
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:120]
