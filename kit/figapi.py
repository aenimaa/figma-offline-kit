"""Minimal Figma REST client. The token comes from $FIGMA_TOKEN or <workspace>/workstation/.env and is never printed.

Pacing rules (learned on a 70-file team): ≥ 1.5 s between calls per process, honour Retry-After in full,
and on outages wait until Figma is reachable again instead of skipping ahead."""
import http.client
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

API = os.environ.get("FIGMA_KIT_API", "https://api.figma.com")  # override only for tests (fake server)
MIN_GAP = float(os.environ.get("FIGMA_KIT_MIN_GAP", 1.5))  # lower only for tests against the fake server
_last = [0.0]
_lock = threading.Lock()


class Stopped(Exception):
    """The person asked to pause (STOP file): raised from waits and downloads so it takes effect within seconds."""


class FigmaError(RuntimeError):
    def __init__(self, status, path, body=""):
        super().__init__(f"{status} on {path}")
        self.status, self.path, self.body = status, path, body


def read_token(ws=None):
    """Return (token, source) or (None, None). The source names where it came from; the token itself stays in memory."""
    tok = os.environ.get("FIGMA_TOKEN", "").strip()
    if tok:
        return tok, "environment variable FIGMA_TOKEN"
    if ws and os.path.exists(ws.env_path):
        with open(ws.env_path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line.startswith("FIGMA_TOKEN="):
                    tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if tok:
                        return tok, "workstation/.env"
    return None, None


def team_id(link):
    """Team id from a team link (…/files/team/123/Name, …/files/<org>/team/123/…) or a bare number."""
    link = (link or "").strip()
    if link.isdigit():
        return link
    m = re.search(r"figma\.com/files/(?:[^/]+/)*team/(\d+)", link)
    return m.group(1) if m else None


def file_keys(text):
    """File keys from one or more file links (design, file, board, slides, proto, make), in order, no repeats."""
    keys = re.findall(r"figma\.com/(?:design|file|board|slides|deck|proto|make)/([A-Za-z0-9]{10,})", text or "")
    return list(dict.fromkeys(keys))


def _say(log, msg):
    (log or (lambda m: print(m, flush=True)))(msg)


# Set by the background run so the guided start can show waits and wake them: WAIT_HOOK(kind, seconds) is called
# before each wait ("network", "server", "rate"); RETRY_HOOK() returns True when the person asked to retry now.
WAIT_HOOK = None
RETRY_HOOK = None
STOP_HOOK = None  # set by the background run: True once the person asked to pause

IDLE_TIMEOUT = float(os.environ.get("FIGMA_KIT_IDLE_TIMEOUT", 60))  # no byte for this long → the read fails
MIN_SPEED = 20_000  # bytes/s: a download slower than this (a stalled connection) fails and is tried again
BASE_DEADLINE = 60  # seconds every read gets on top of size / MIN_SPEED


def check_stop():
    if STOP_HOOK and STOP_HOOK():
        raise Stopped()


def nap(seconds, kind=None):
    """Sleep, but wake early when the person asks to retry now; a pause request ends it at once (Stopped)."""
    if kind and WAIT_HOOK:
        WAIT_HOOK(kind, seconds)
    end = time.time() + seconds
    while time.time() < end:
        check_stop()
        if RETRY_HOOK and RETRY_HOOK():
            return
        time.sleep(min(1.0, max(0.0, end - time.time())))


def read_all(resp, limit=None):
    """Read a whole response with a total deadline as well as the socket's idle timeout: a connection that trickles
    a few bytes now and then never trips the idle timeout, so it would hang for hours. The deadline is
    60 s + size / 20 kB/s (10 min when the size is unknown). Raises TimeoutError, which callers retry."""
    size = int(resp.headers.get("Content-Length") or 0) if getattr(resp, "headers", None) else 0
    deadline = time.time() + (limit or (BASE_DEADLINE + size / MIN_SPEED if size else 10 * BASE_DEADLINE))
    parts = []
    read = getattr(resp, "read1", resp.read)  # read1 returns what has arrived; read(n) would wait for all n bytes
    while True:
        check_stop()
        chunk = read(65536)
        if not chunk:
            return b"".join(parts)
        parts.append(chunk)
        if time.time() > deadline:
            raise TimeoutError(f"download too slow ({sum(map(len, parts)) // 1024} kB in time): the connection stalled")


def get(path, token, tries=6, timeout=None, log=None, outage_max_wait=300):
    """GET a Figma endpoint and return parsed JSON. Raises FigmaError on a non-retryable HTTP error."""
    url = path if path.startswith("http") else API + path
    short = path[:60]
    for i in range(tries):
        with _lock:
            gap = _last[0] + MIN_GAP - time.time()
            if gap > 0:
                time.sleep(gap)
            _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"X-Figma-Token": token})
            with urllib.request.urlopen(req, timeout=timeout or IDLE_TIMEOUT) as r:
                return json.loads(read_all(r))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 0) or 60 * (i + 1)
                until = time.strftime("%H:%M", time.localtime(time.time() + wait))
                _say(log, f"  Figma asked to slow down ({short}) → waiting {wait}s (until {until})")
                nap(wait + 5, "rate")
                continue
            if e.code >= 500 and i < tries - 1:
                wait = min(2 ** (i + 2), outage_max_wait)
                _say(log, f"  Figma had a problem ({e.code} on {short}) → trying again in {wait}s")
                nap(wait, "server")
                continue
            body = e.read()[:600].decode("utf-8", "replace")
            e.close()
            raise FigmaError(e.code, path, body)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException) as e:
            if i == tries - 1:
                raise
            wait = min(2 ** (i + 2), outage_max_wait)
            _say(log, f"  can't reach Figma: check your internet or VPN ({str(e)[:60]}) → trying again in {wait}s")
            nap(wait, "network")
    raise RuntimeError(f"gave up on {path} after {tries} tries")


def reachable(timeout=10):
    """True if api.figma.com answers at all (any HTTP status counts). No token is sent."""
    try:
        urllib.request.urlopen(urllib.request.Request(API + "/v1/me"), timeout=timeout)
        return True, ""
    except urllib.error.HTTPError:
        return True, ""
    except Exception as e:  # noqa: BLE001 - any failure means "not reachable"
        return False, str(e)[:120]
