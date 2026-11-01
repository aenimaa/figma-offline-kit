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


def retry_path(ws):
    """The guided start writes this file when the person presses R: a wait for Figma ends early."""
    return os.path.join(ws.station, "RETRY")


def waiting_path(ws):
    """What the run is waiting for, if anything: {"kind": network|server|rate, "until": epoch seconds}."""
    return os.path.join(ws.station, "waiting.json")


def request_retry(ws):
    write_text(retry_path(ws), "retry now\n")


def _hooks(ws):
    def on_wait(kind, seconds):
        write_json(waiting_path(ws), {"kind": kind, "until": time.time() + seconds})

    def retry_now():
        if os.path.exists(retry_path(ws)):
            try:
                os.remove(retry_path(ws))
            except OSError:
                pass
            return True
        return False
    figapi.WAIT_HOOK, figapi.RETRY_HOOK = on_wait, retry_now
    figapi.STOP_HOOK = lambda: os.path.exists(stop_path(ws))


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


NOTE = {  # the run section's note: (English, Persian)
    "finished": ("finished: {done} done, {failed} failed", "تمام شد: {done} فایل کامل، {failed} ناموفق"),
    "ended": ("ended unexpectedly ({why}); resume to continue", "ناگهان تمام شد ({why})؛ با ادامه دادن از همان‌جا پیش می‌رود"),
    "paused": ("paused: {why}; resume to continue", "متوقف شد: {why}؛ با ادامه دادن از همان‌جا پیش می‌رود"),
}
WHY_FA = {"stopped on request": "به درخواست شما"}
PHASE_FA = {"running": "در حال اجرا", "paused": "متوقف", "exported": "خروجی کامل", "closed": "وارسی و بسته شد",
            "planned": "برنامه‌ریزی شده", "interviewed": "تنظیم شده"}


def render(ws, plan, note=None, lang=None):
    """The run section of REPORT.md. `note` is (NOTE key, values) or None; Persian when the settings say so."""
    from .i18n import fa_digits
    fa = (lang or (ws.config() or {}).get("language")) == "fa"
    F = fa_digits if fa else str
    q, done, failed, st = progress(ws, plan)
    shots = sum(st[x["key"]].get("screens", 0) for x in done)
    phase = ws.state().get("phase")
    text = ""
    if note:
        key, kw = note
        kw = {k: (F(v) if isinstance(v, int) else v) for k, v in kw.items()}
        if fa and "why" in kw:
            w = kw["why"]
            kw["why"] = WHY_FA.get(w) or (w.replace("project ", "پروژهٔ ").replace("file ", "فایل ").replace(" finished", " تمام شد"))
        text = NOTE[key][1 if fa else 0].format(**kw)
    if fa:
        lines = ["# اجرا", "", f"به‌روز شده در {now_iso()[:16].replace('T', ' ')} · **{PHASE_FA.get(phase, phase)}**"
                 + (f" · {text}" if text else ""), "",
                 f"**{F(len(done))} از {F(len(q))} فایل** تمام · {F(shots)} فریم" + (f" · {F(len(failed))} ناموفق" if failed else ""), "",
                 "| پروژه | فایل | فریم | وضعیت |", "|---|---|---|---|"]
        states = {"done": lambda r: f"✔ {F(r.get('minutes', '?'))} دقیقه", "failed": lambda r: f"✖ {(r.get('error') or '')[:80]}",
                  "running": lambda r: "… در حال کار"}
        waiting = "در صف"
    else:
        lines = ["# Run", "", f"Updated {now_iso()} · **{phase}**" + (f" · {text}" if text else ""), "",
                 f"**{len(done)} / {len(q)} files** done · {shots} screens" + (f" · {len(failed)} failed" if failed else ""), "",
                 "| Project | File | Screens | State |", "|---|---|---|---|"]
        states = {"done": lambda r: f"✔ {r.get('minutes', '?')} min", "failed": lambda r: f"✖ {(r.get('error') or '')[:80]}",
                  "running": lambda r: "… working"}
        waiting = "waiting"
    for x in q:
        r = st.get(x["key"], {})
        s = r.get("status", "waiting")
        state = states[s](r) if s in states else waiting
        href = "backup/" + quote(x["dir"].replace(os.sep, "/")) + "/index.html"  # REPORT.md is at the top
        link = f"[{x['name']}]({href})" if s == "done" else x["name"]
        n = r.get("screens")
        lines.append(f"| {x['project']} | {link} | {F(n) if n is not None else '—'} | {state} |")
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
    for leftover in (retry_path(ws), waiting_path(ws)):
        if os.path.exists(leftover):
            os.remove(leftover)
    _hooks(ws)
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
        _, done, failed, files = progress(ws, plan)
        ws.set_phase("exported", pid=None, finished=now_iso())
        report.log(ws, "run_done", who="kit", failed=len(failed),
                   screens=sum(files[x["key"]].get("screens", 0) for x in done))
        report.update(ws, "run", render(ws, plan, ("finished", {"done": len(done), "failed": len(failed)})))
        log(f"{time.strftime('%H:%M')} finished: {len(done)} done, {len(failed)} failed")
        return 0
    except BaseException as e:
        ws.set_phase("paused", pid=None, note=f"ended: {type(e).__name__}")
        report.log(ws, "run_ended", who="kit", why=type(e).__name__)
        report.update(ws, "run", render(ws, plan, ("ended", {"why": type(e).__name__})))
        raise


def wait_for_figma(log, every=60):
    """Outage: wait until api.figma.com answers again (never skip ahead). R in the guided start retries at once."""
    while not figapi.reachable()[0]:
        log(f"{time.strftime('%H:%M')} Can't reach Figma: check your internet or VPN. Trying again in {every}s")
        figapi.nap(every, "network")


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
    report.log(ws, "run_paused", who="kit", why=why)
    report.update(ws, "run", render(ws, plan, ("paused", {"why": why})))
    log(f"{time.strftime('%H:%M')} paused: {why}")
    return 0


def request_stop(ws):
    write_text(stop_path(ws), now_iso() + "\n")
