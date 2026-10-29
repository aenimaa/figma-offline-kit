"""Run: work through plan.json file by file (screens → export → gallery), keeping state.json and REPORT.md current.

`kit.py run` starts this detached, so it survives closing the AI app; `--foreground` runs it in the console.
Modes: full (to the end) · project (pause after each project) · file (pause after each file). Resume = run again."""
import os
import subprocess
import sys
import time
from urllib.parse import quote

from . import export, figapi, gallery, report
from .util import REPO, now_iso, read_json, write_json, write_text


def pid_alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def running(ws):
    st = ws.state()
    return st.get("phase") == "running" and pid_alive(st.get("pid"))


def stop_path(ws):
    return os.path.join(ws.station, "STOP")


def start_detached(ws, args=("run",), log_name="run.log"):
    """Start `kit.py <args> --foreground` as its own process, logging to workstation/logs/<log_name>."""
    log = open(os.path.join(ws.logs, log_name), "a", encoding="utf-8")
    cmd = [sys.executable, "-X", "utf8", os.path.join(REPO, "kit.py"), *args, "--foreground", "--workspace", ws.root]
    kw = {"stdout": log, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL, "cwd": REPO,
          "env": dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")}
    if os.name == "nt":
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:  # also leave the AI app's job object, so closing the app doesn't end the run
            return subprocess.Popen(cmd, creationflags=flags | 0x01000000, **kw).pid
        except OSError:
            return subprocess.Popen(cmd, creationflags=flags, **kw).pid
    return subprocess.Popen(cmd, start_new_session=True, **kw).pid


def progress(ws, plan):
    st = ws.state().get("files", {})
    q = [x for x in plan["queue"] if x["pages"]]
    done = [x for x in q if st.get(x["key"], {}).get("status") == "done"]
    failed = [x for x in q if st.get(x["key"], {}).get("status") == "failed"]
    return q, done, failed, st


def render(ws, plan, note=""):
    q, done, failed, st = progress(ws, plan)
    shots = sum(st[x["key"]].get("screens", 0) for x in done)
    phase = ws.state().get("phase")
    lines = ["# Run", "", f"Updated {now_iso()} · **{phase}**" + (f" · {note}" if note else ""), "",
             f"**{len(done)} / {len(q)} files** done · {shots} screens" + (f" · {len(failed)} failed" if failed else ""), "",
             "| Project | File | Screens | State |", "|---|---|---|---|"]
    for x in q:
        r = st.get(x["key"], {})
        s = r.get("status", "waiting")
        state = {"done": f"✔ {r.get('minutes', '?')} min", "failed": f"✖ {(r.get('error') or '')[:80]}",
                 "running": "… working"}.get(s, "waiting")
        href = "../backup/" + quote(x["dir"].replace(os.sep, "/")) + "/index.html"
        link = f"[{x['name']}]({href})" if s == "done" else x["name"]
        lines.append(f"| {x['project']} | {link} | {r.get('screens', '—')} | {state} |")
    return "\n".join(lines) + "\n"


def set_file(ws, key, **rec):
    st = ws.state()
    st.setdefault("files", {}).setdefault(key, {}).update(rec)
    st["updated"] = now_iso()
    write_json(ws.state_path, st)


def run(ws, log=print):
    cfg = ws.config()
    plan = read_json(os.path.join(ws.station, "plan.json"))
    token, _ = figapi.read_token(ws)
    if os.path.exists(stop_path(ws)):
        os.remove(stop_path(ws))
    ws.set_phase("running", pid=os.getpid(), started=now_iso())
    stop = lambda: os.path.exists(stop_path(ws))  # noqa: E731
    q, _, _, _ = progress(ws, plan)
    log(f"{time.strftime('%H:%M')} run: {len(q)} files with pages · mode {cfg['mode']}")
    worked = None  # project of the last file this run actually exported
    try:
        for i, item in enumerate(q):
            if ws.state().get("files", {}).get(item["key"], {}).get("status") == "done":
                continue  # changed files are refreshed by the drift check, not here
            if cfg["mode"] == "project" and worked is not None and item["project"] != worked:
                return pause(ws, plan, f"project {worked} finished", log)
            if stop():
                return pause(ws, plan, "stopped on request", log)
            log(f"{time.strftime('%H:%M')} → {item['project']} / {item['name']}")
            set_file(ws, item["key"], status="running")
            report.update(ws, "run", render(ws, plan))
            t0 = time.time()
            try:
                sc, res = one_file(ws, item, token, cfg, log, stop)
                set_file(ws, item["key"], status="done", screens=len(sc["screens"]), empty=len(res["empty"]), empty_ids=res["empty"],
                         minutes=round((time.time() - t0) / 60, 1), exported=now_iso(),
                         last_modified=item.get("last_modified"), error=None)
                log(f"{time.strftime('%H:%M')} ✔ {item['name']}: {len(sc['screens'])} screens")
            except export.Stopped:
                set_file(ws, item["key"], status="waiting")
                return pause(ws, plan, "stopped on request", log)
            except Exception as e:  # noqa: BLE001 - one bad file must not end the run
                set_file(ws, item["key"], status="failed", error=str(e)[:300])
                log(f"{time.strftime('%H:%M')} ✖ {item['name']}: {e}")
            worked = item["project"]
            report.update(ws, "run", render(ws, plan))
            if cfg["mode"] == "file" and i < len(q) - 1:
                return pause(ws, plan, f"file {item['name']} finished", log)
        _, done, failed, _ = progress(ws, plan)
        ws.set_phase("exported", pid=None, finished=now_iso())
        report.update(ws, "run", render(ws, plan, f"finished: {len(done)} done, {len(failed)} failed"))
        log(f"{time.strftime('%H:%M')} finished: {len(done)} done, {len(failed)} failed")
        return 0
    except BaseException as e:
        ws.set_phase("paused", pid=None, note=f"ended: {type(e).__name__}")
        report.update(ws, "run", render(ws, plan, f"ended unexpectedly ({type(e).__name__}); resume to continue"))
        raise


def wait_for_figma(log, every=60):
    """Outage: wait until api.figma.com answers again (never skip ahead)."""
    while not figapi.reachable()[0]:
        log(f"{time.strftime('%H:%M')} Figma not reachable, checking again in {every}s")
        time.sleep(every)


def one_file(ws, item, token, cfg, log, stop, tries=3):
    for attempt in range(tries):
        try:
            sc = export.list_screens(ws, item, token, log=log)
            res = export.export(ws, sc, token, cfg["formats"], log=log, stop=stop)
            gallery.build(ws, sc)
            return sc, res
        except figapi.FigmaError as e:
            if e.status < 500 or attempt == tries - 1:
                raise
        except (OSError, RuntimeError):  # network trouble or Figma gave up: wait, then retry the same file
            if attempt == tries - 1:
                raise
        log(f"  retrying {item['name']} once Figma answers")
        wait_for_figma(log)


def pause(ws, plan, why, log):
    ws.set_phase("paused", pid=None, note=why)
    report.update(ws, "run", render(ws, plan, f"paused: {why}; resume to continue"))
    log(f"{time.strftime('%H:%M')} paused: {why}")
    return 0


def request_stop(ws):
    write_text(stop_path(ws), now_iso() + "\n")
