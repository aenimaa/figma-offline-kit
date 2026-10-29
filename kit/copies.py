"""Local copies (.fig / .jam / .deck / .make) saved from Figma desktop with "Save local copy".

There's no API for this: either the AI drives Figma desktop (automatic, needs desktop control) or the user presses
Save (guided). The kit keeps the checklist, opens files, paces the saves, and files and checks what lands on disk.

Pacing: Figma starts bot checks after ≈ 40 saves a day or quick runs, so ≤ 40 a day and ≥ 60 s between files."""
import datetime
import os
import platform
import re
import shutil
import subprocess
import time

from .names import lp, safe
from .util import now_iso, read_json, write_json

EXT = {"figma": ".fig", "figjam": ".jam", "slides": ".deck", "make": ".make"}
SCHEME = {"slides": "figma://slides/{key}"}  # everything else opens with figma://file/{key}
MAGIC = (b"PK", b"fig-kiwi")
PER_DAY, GAP = 40, 60


def path(ws):
    return os.path.join(ws.station, "copies.json")


def sync(ws):
    """Bring copies.json in line with the plan: one entry per file Figma desktop can save. Keeps progress."""
    plan = read_json(os.path.join(ws.station, "plan.json"), {"queue": []})
    old = read_json(path(ws), {"items": {}})
    items = {}
    for q in plan["queue"]:
        ext = EXT.get(q["editorType"])
        if not ext:
            continue
        rec = old["items"].get(q["key"], {"status": "todo"})
        rec.update(key=q["key"], name=q["name"], project=q["project"], editorType=q["editorType"],
                   target=os.path.join(ws.backup, q["dir"], safe(q["name"]) + ext),
                   url=SCHEME.get(q["editorType"], "figma://file/{key}").format(key=q["key"]))
        items[q["key"]] = rec
    old["items"] = items
    write_json(path(ws), old)
    return old


def ordered(data):
    return sorted(data["items"].values(), key=lambda r: (r["project"].casefold(), r["name"].casefold()))


def find(data, ref):
    rows = ordered(data)
    for n, r in enumerate(rows, 1):
        if ref in (str(n), r["key"]) or ref.casefold() == r["name"].casefold():
            return r
    raise ValueError(f"no file '{ref}' in the local-copy list (use its number from `kit.py copies`, its name or key)")


def opened_today(data):
    today = datetime.date.today().isoformat()
    return [r for r in data["items"].values() if (r.get("opened") or "")[:10] == today]


def wait_seconds(data):
    """0 if a file may be opened now; otherwise seconds to wait (or -1: the daily limit is reached)."""
    if len(opened_today(data)) >= PER_DAY:
        return -1
    last = max((r.get("opened_ts", 0) for r in data["items"].values()), default=0)
    return max(0, int(last + GAP - time.time()))


def launch(url):
    sysname = platform.system()
    if sysname == "Windows":
        os.startfile(url)  # noqa: S606 - opens the figma:// link in Figma desktop
    elif sysname == "Darwin":
        subprocess.Popen(["open", url])
    else:
        subprocess.Popen(["xdg-open", url])


def open_file(ws, ref, force=False, launch_fn=launch):
    data = sync(ws)
    r = find(data, ref)
    w = wait_seconds(data)
    if w and not force:
        raise ValueError("daily limit of ≈ 40 local copies reached: continue tomorrow" if w < 0
                         else f"wait {w} s before the next file (Figma's bot checks)")
    os.makedirs(lp(os.path.dirname(r["target"])), exist_ok=True)
    launch_fn(r["url"])
    data["items"][r["key"]].update(status="opened", opened=now_iso(), opened_ts=time.time())
    write_json(path(ws), data)
    return data["items"][r["key"]]


def valid(p):
    try:
        if os.path.getsize(lp(p)) == 0:
            return False
        with open(lp(p), "rb") as f:
            head = f.read(8)
        return head.startswith(MAGIC)
    except OSError:
        return False


def _norm(s):
    return re.sub(r"[^0-9a-z]+", "", (s or "").casefold())


def inboxes(ws):
    """Where a guided save may land: the workspace inbox and the user's Downloads folder."""
    return [os.path.join(ws.temp, "incoming"), os.path.join(os.path.expanduser("~"), "Downloads")]


def check(ws, log=print):
    """Tick off every copy that is on disk and valid. Files saved to an inbox under the file's name are moved into place."""
    data = sync(ws)
    found = []
    for r in ordered(data):
        if r["status"] in ("done", "skipped"):
            continue
        ext = os.path.splitext(r["target"])[1]
        if not os.path.exists(lp(r["target"])):
            since = r.get("opened_ts", 0) - 5
            for box in inboxes(ws):
                if not os.path.isdir(box):
                    continue
                for fn in os.listdir(box):
                    stem, e = os.path.splitext(fn)
                    stem = re.sub(r"\s*\(\d+\)$", "", stem)  # "Name (1).fig" from repeated saves
                    p = os.path.join(box, fn)
                    if e.lower() == ext and _norm(stem) == _norm(r["name"]) and os.path.getmtime(p) >= since and valid(p):
                        shutil.move(p, lp(r["target"]))
                        log(f"  moved {fn} → {os.path.relpath(r['target'], ws.root)}")
                        break
                if os.path.exists(lp(r["target"])):
                    break
        if os.path.exists(lp(r["target"])):
            if valid(r["target"]):
                r.update(status="done", done=now_iso(), size=os.path.getsize(lp(r["target"])), note=None)
                found.append(r)
            else:
                r.update(status="failed", note="file on disk is empty or not a Figma file")
        data["items"][r["key"]] = r
    write_json(path(ws), data)
    return found


def skip(ws, ref, reason):
    data = sync(ws)
    r = find(data, ref)
    data["items"][r["key"]].update(status="skipped", note=reason or "skipped by the user")
    write_json(path(ws), data)


def watch(ws, minutes=30, every=5, log=print):
    """Guided mode: keep checking until every opened file is saved (or time runs out)."""
    end = time.time() + minutes * 60
    while time.time() < end:
        for r in check(ws, log=lambda m: None):
            log(f"  ✔ {r['name']} ({r['size'] / 2**20:.1f} MB)")
        data = read_json(path(ws))
        if not any(r["status"] == "opened" for r in data["items"].values()):
            return True
        time.sleep(every)
    return False


def render(ws):
    data = sync(ws)
    rows = ordered(data)
    done = sum(r["status"] == "done" for r in rows)
    w = wait_seconds(data)
    lines = ["# Local copies", "",
             f"**{done} / {len(rows)}** saved · opened today: {len(opened_today(data))} / {PER_DAY} · "
             + ("next file: now" if w == 0 else "daily limit reached: continue tomorrow" if w < 0 else f"next file in {w} s"), "",
             "| # | Project | File | Copy | State |", "|---|---|---|---|---|"]
    sym = {"done": "✔", "opened": "… open in Figma", "failed": "✖", "skipped": "⏭", "todo": ""}
    for n, r in enumerate(rows, 1):
        st = sym.get(r["status"], r["status"])
        if r["status"] == "done":
            st += f" {r.get('size', 0) / 2**20:.1f} MB"
        if r.get("note"):
            st += f" ({r['note']})"
        lines.append(f"| {n} | {r['project']} | {r['name']} | {os.path.splitext(r['target'])[1]} | {st} |")
    return "\n".join(lines) + "\n"
