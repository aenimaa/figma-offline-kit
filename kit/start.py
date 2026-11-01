"""Guided start: one terminal window that walks a person through the whole backup, step by step, in English or Persian.

`python kit.py start [--lang fa|en]`, or double-click Start.bat (Windows) / Start.command (macOS). It picks up where
the job stands, so running it again shows progress, offers to pause, or offers the next step. It's for people
without an AI: no command hints, plain checklists, friendlier defaults."""
import argparse
import getpass
import os
import platform
import shutil
import subprocess
import sys
import time

from . import doctor, export, figapi, interview, pages, plan, report, runner
from .figapi import read_token
from .i18n import NO, YES, normalize, num, plan_summary, t
from .util import REPO, guide, md_plain, read_json, wrap, write_json
from .workspace import Workspace, remember, resolve, save_token, take_token_file, token_file_path

STEPS = 6
RTL_TERMINAL = os.name == "nt"  # Windows consoles have no right-to-left layout (no bidi)
NO_AI = {"desktop-control": "no", "figma-mcp": "no"}  # a person in a terminal, not an AI
STALL = 120  # seconds without a new screen before the live view says so
HOLD = 10  # seconds without a new screen before the time-left estimate stops moving


def _ns(ws_arg, **kw):
    d = dict(workspace=ws_arg, json=False, ai="", offline=False, answers=None, choose=None, edit=False,
             confirm=False, foreground=False, guided=True)
    d.update(kw)
    return argparse.Namespace(**d)


class Wizard:
    def __init__(self, ws_arg, inp, lang, secret, open_file, open_page):
        self.ws_arg, self.inp, self.lang = ws_arg, inp, lang
        self.secret = secret or getpass.getpass
        self.open_file = open_file or _open_in_editor
        self.open_page = open_page or _open
        self.open_folder = open_page or _open_folder
        self.poll = None

    def say(self, key, **kw):
        print(wrap(t(key, self.lang, **kw)))

    def path(self, p):
        print(f"  {p}")

    def yes(self, key, default=True, **kw):
        q = wrap(t(key, self.lang, **kw))
        while True:
            raw = normalize(self.inp(f"{q} {t('yes_no' if default else 'no_yes', self.lang)}: "))
            if not raw:
                return default
            if raw in YES:
                return True
            if raw in NO:
                return False

    def step(self, n, key):
        title = t(key, self.lang)
        print(f"\n── {t('step', self.lang, n=n, total=STEPS, title=title)} " + "─" * max(0, 34 - len(title)))


def inside_zip(path=REPO):
    """True when Windows runs the kit straight from a ZIP (Explorer copies it to a '…\\Temp1_name.zip\\' folder)."""
    return any(part.lower().endswith(".zip") for part in os.path.normpath(path).split(os.sep))


def ask_language(inp, preset=None):
    """The first question. Returns 'fa' or 'en': the language of the report and pages, and of this window where the
    terminal can show Persian. Windows terminals show Persian reversed and unjoined (no right-to-left layout), so
    there the menu has no Persian script and the window stays English."""
    if preset in ("fa", "en"):
        return preset
    if RTL_TERMINAL:
        print("\nLanguage of your report and pages")
        print("  1. Persian (Farsi): REPORT.md and pages in Persian; this window stays in English")
        print("  2. English")
    else:
        print("\nLanguage / زبان")
        print("  1. فارسی (Persian)")
        print("  2. English")
    while True:
        raw = normalize(inp("> [2] "))
        if raw in ("", "2", "en", "english"):
            return "en"
        if raw in ("1", "fa", "فارسی", "persian", "farsi"):
            return "fa"


def window_language(lang):
    """The language this window can show: English on Windows, else the chosen one."""
    return "en" if RTL_TERMINAL else lang


def editor_name():
    return {"Windows": "Notepad", "Darwin": "TextEdit"}.get(platform.system(), "your text editor")


def token_step(w, ws, drop=None):
    """Get the token into <workspace>/workstation/.env and check it with Figma. True to go on, False to stop for now.
    `drop` is the visible token file next to Start (download only)."""
    drop = drop if drop is not None else token_file_path()
    while True:
        if drop and take_token_file(ws, drop):
            w.say("token_moved", name=os.path.basename(drop))
            w.path(ws.env_path)
            report.log(ws, "token")
        tok, source = read_token(ws)
        if tok:
            try:
                me = figapi.get("/v1/me", tok, tries=1, timeout=20, log=lambda m: None)
                w.say("token_works", who=me.get("handle", "?"))
                return True
            except figapi.FigmaError as e:
                if e.status not in (401, 403):
                    w.say("token_untested")
                    return True
                w.say("token_refused", status=e.status)
                if source != "workstation/.env":
                    print("  (FIGMA_TOKEN environment variable)")
                    return False
            except Exception:  # noqa: BLE001 - offline, proxy, certificates: the check step explains
                w.say("token_untested")
                return True
        w.say("token_need")
        w.path(guide("figma-token.md"))
        w.say("token_where")
        w.path(ws.env_path)
        if drop and os.path.exists(drop):
            w.say("token_drop")
            w.path(drop)
        elif platform.system() == "Darwin":
            w.say("token_hidden_file")
        print(t("token_menu", w.lang, editor=editor_name()))
        raw = normalize(w.inp(t("choice", w.lang)))
        if raw in ("1", ""):
            pasted = w.secret(wrap(t("token_paste", w.lang)))
            if pasted.strip():
                save_token(ws, pasted)
                w.say("token_saved")
                w.path(ws.env_path)
                report.log(ws, "token")
            else:
                w.say("token_empty")
        elif raw == "2":
            target = drop if drop and os.path.exists(drop) else ws.env_path
            try:
                w.open_file(target)
                w.inp(wrap(t("token_opened", w.lang, editor=editor_name())) + " ")
            except OSError:
                w.say("token_open_failed")
        elif raw == "3":
            w.say("token_later")
            return False


def check_step(w, ws):
    """Doctor as a short checklist. True if the backup can go on."""
    was_ready = (read_json(ws.doctor_path) or {}).get("core_ready")
    r = doctor.run(ws, ai=NO_AI)
    report.update(ws, "doctor", doctor.render(r, report.lang_of(ws)))
    failing = [doctor.LABELS.get(k, k) for k, v in r["checks"].items() if v["required"] and v["status"] != doctor.OK]
    if r["core_ready"] != was_ready:  # log changes only, not every re-check
        report.log(ws, "doctor_ok" if r["core_ready"] else "doctor_no", items=", ".join(failing))
    if r["core_ready"] and was_ready:
        w.say("still_ready")  # later runs: one line; the full list only when something is wrong
    else:
        print(doctor.render_plain(r, w.lang))
    return r["core_ready"]


def backup_summary(ws, lang):
    """'Onboarding, Landing · 1 of 2 files done · 18 screens' for a backup found on disk."""
    p = read_json(os.path.join(ws.station, "plan.json"))
    cfg = ws.config()
    if not p:
        src = cfg["team"]["id"] or ", ".join(cfg.get("files", []))[:40]
        return t("found_none", lang, src=src)
    q, done, _, files = runner.progress(ws, p)
    names = ", ".join(x["name"] for x in q[:2]) + (" …" if len(q) > 2 else "")
    screens = sum(files[x["key"]].get("screens", 0) for x in done)
    running = next((x for x in q if files.get(x["key"], {}).get("status") in ("running", "waiting")), None)
    if running:  # a file cut off half way: count what is on disk
        sc = read_json(export.screens_path(ws, running["key"]))
        if sc:
            screens += sum(1 for s in sc["screens"] if os.path.exists(export.target(ws, sc, s, "png")))
    return t("found_what", lang, names=names, done=len(done), files=len(q), screens=screens)


def show_progress(w, ws, p):
    q, done, failed, files = runner.progress(ws, p)
    screens = sum(files[x["key"]].get("screens", 0) for x in done)
    w.say("progress", done=len(done), files=len(q), screens=screens,
          failed=t("failed_n", w.lang, n=len(failed)) if failed else "")
    current = next((x["name"] for x in q if files.get(x["key"], {}).get("status") == "running"), None)
    if current:
        w.say("now", name=current)


def key_poller():
    """poll(seconds) → a lower-case key pressed in this window, or None after `seconds`. No Enter needed."""
    if not sys.stdin.isatty():
        return lambda seconds: (time.sleep(seconds), None)[1]
    if os.name == "nt":
        import msvcrt

        def poll(seconds):
            end = time.time() + seconds
            while time.time() < end:
                if msvcrt.kbhit():
                    return msvcrt.getwch().lower()
                time.sleep(0.1)
            return None
        return poll
    import select
    import termios
    import tty

    def poll(seconds):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ready, _, _ = select.select([sys.stdin], [], [], seconds)
            return sys.stdin.read(1).lower() if ready else None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return poll


def _minutes(seconds, lang):
    m = max(1, round(seconds / 60))
    return num(f"{m} min" if lang != "fa" else f"{m} دقیقه", lang)


def status_line(w, ws, p, started, base_screens, hold=None):
    """One line: the current file, its PNG / SVG counts on disk, time so far and time left. Returns (line, what
    changed, time-left text). `hold`: the last time-left text, kept (with "waiting…") while nothing moves."""
    q, done, _, files = runner.progress(ws, p)
    cur = next((x for x in q if files.get(x["key"], {}).get("status") == "running"), None)
    sc = read_json(export.screens_path(ws, cur["key"])) if cur else None
    if not cur or not sc:
        return t("starting", w.lang), (len(done), None), None
    total = len(sc["screens"])
    have = {ext: sum(1 for s in sc["screens"] if os.path.exists(export.target(ws, sc, s, ext))
                     or (ext == "svg" and os.path.exists(export.target(ws, sc, s, "pdf"))))
            for ext in ("png", "svg")}
    fmts = ws.config()["formats"]
    finished = sum(files[x["key"]].get("screens", 0) for x in done)
    now_done = finished + sum(have[e] for e in fmts) / max(len(fmts), 1)
    left = sum(x.get("est", 0) for x in q if x not in done and x is not cur) + max(total - now_done + finished, 0)
    elapsed = time.time() - started
    rate = (now_done - base_screens) / elapsed if elapsed > 30 and now_done > base_screens else \
        plan.SCREENS_PER_MIN[min(len(fmts), 2)] / 60
    left_txt = t("left", w.lang, min=max(1, round(left / rate / 60))) if left > 0.5 else t("left_soon", w.lang)
    shown_left = f"{hold} · {t('waiting', w.lang)}" if hold else left_txt
    cnt = {e: (num(f"{have[e]}/{total}", w.lang) if e in fmts else "–") for e in ("png", "svg")}
    return (t("watch_line", w.lang, file=cur["name"], png=cnt["png"], svg=cnt["svg"],
              elapsed=_minutes(elapsed, w.lang), left=shown_left), (len(done), cur["key"], have["png"], have["svg"]),
            left_txt)


def watch(w, ws, p, sleep=3):
    """Show the background run live until it stops: per-file lines, one status line, outages with R to retry now
    and P to pause. Returns 'exported', 'paused', 'stopped' (process gone) or 'detached' (Enter)."""
    from . import cli
    poll = w.poll or key_poller()
    w.say("watch_intro")
    q, done, failed, _ = runner.progress(ws, p)
    reported = {x["key"] for x in done + failed}
    base = sum(ws.state()["files"][x["key"]].get("screens", 0) for x in done)
    started, width, shown, told = time.time(), 0, "", None
    last_sig, last_change, last_left = None, time.time(), None

    def show(line):
        nonlocal width
        line = line[:max(20, shutil.get_terminal_size((80, 24)).columns - 1)]
        print("\r" + line.ljust(width), end="", flush=True)
        width = len(line)

    def say_line(text):
        nonlocal width, shown
        print("\r" + " " * width + "\r" + text, flush=True)
        width, shown = 0, ""  # the status line is drawn again below it

    while True:
        q, done, failed, files = runner.progress(ws, p)
        for x in done + failed:
            if x["key"] not in reported:
                reported.add(x["key"])
                rec = files[x["key"]]
                say_line(wrap(t("file_done", w.lang, name=x["name"], n=rec.get("screens", 0)) if rec["status"] == "done"
                              else t("file_failed", w.lang, name=x["name"], error=(rec.get("error") or "")[:120])))
        if not runner.running(ws):
            break
        wait = read_json(runner.waiting_path(ws)) or {}
        secs = round(wait.get("until", 0) - time.time())
        if secs > -3:  # the run is waiting: say why once, then count down on the status line
            kind = wait.get("kind", "network")
            if told != (kind, wait.get("until")):
                told = (kind, wait.get("until"))
                say_line(wrap(t({"server": "wait_server", "rate": "wait_rate"}.get(kind, "wait_network"), w.lang)))
            line = t("wait_count_rate" if kind == "rate" else "wait_count", w.lang, secs=max(secs, 0))
        else:
            line, sig, left = status_line(w, ws, p, started, base)
            if sig != last_sig:
                last_sig, last_change, last_left = sig, time.time(), left
            elif time.time() - last_change > HOLD and last_left:  # nothing moves: keep the last estimate
                line = status_line(w, ws, p, started, base, hold=last_left)[0]
            if sig == last_sig and time.time() - last_change > STALL:  # say so instead of a frozen line
                line = t("stalled", w.lang, min=round((time.time() - last_change) / 60))
        if line != shown:
            show(line)
            shown = line
        key = poll(sleep)
        if key == "r":
            runner.request_retry(ws)
            say_line(t("retrying", w.lang))
        elif key == "p":
            cli.cmd_stop(_ns(w.ws_arg))
            say_line(t("pausing", w.lang))
        elif key in ("\r", "\n", "q"):
            say_line("")
            return "detached"
    say_line("")
    phase = ws.state().get("phase")
    if phase == "exported":
        q, done, failed, files = runner.progress(ws, p)
        w.say("run_done", screens=sum(files[x["key"]].get("screens", 0) for x in done), failed=len(failed))
        return "exported"
    if phase == "paused":
        return "paused"
    w.say("run_stopped")
    return "stopped"


def run(ws_arg=None, inp=input, open_page=None, lang=None, secret=None, open_file=None, poll=None):
    if inside_zip():
        print(wrap(t("in_zip", "en")) + "\n\n" + t("in_zip", "fa"))
        return 1
    report.ACTOR["who"] = "start"  # the log says "you, in Start"
    try:
        return _run(ws_arg, inp, open_page, lang, secret, open_file, poll)
    finally:
        report.ACTOR["who"] = None


def _run(ws_arg, inp, open_page, lang, secret, open_file, poll):
    from . import cli  # late import: cli imports this module

    ws = resolve(ws_arg)
    cfg = ws.config() if ws else None
    print(t("title", "en"))
    chosen = ask_language(inp, lang or (cfg or {}).get("language"))  # report language
    w = Wizard(ws_arg, inp, window_language(chosen), secret, open_file, open_page)
    w.poll = poll
    if cfg and cfg.get("language") != chosen:
        cfg["language"] = chosen
        write_json(ws.config_path, cfg)
        report.log(ws, "language", lang="فارسی" if chosen == "fa" else "English")
    if cfg:  # settings in plain words, in the chosen language
        report.update(ws, "config", report.config_md(cfg, ws.env_path))
    w.say("intro")
    if cfg:
        w.say("report_where")
        w.path(ws.report_path)

    if not ws or not cfg:
        w.step(1, "t_setup")
        w.say("setup_intro")
        found = []

        def existing(qid, answers):  # a folder that already holds a backup: continue it, skip the questions
            if qid != "workspace":
                return False
            other = Workspace(os.path.expanduser(answers.get("workspace") or interview.BY_ID["workspace"]["default"]))
            if not other.config():
                return False
            w.say("found_backup", what=backup_summary(other, w.lang))
            if w.yes("continue_q"):
                found.append(other)
                return True
            return False

        answers = interview.ask_terminal(inp, lang=w.lang, preset={"language": chosen}, person=True, after=existing)
        if found:
            ws = found[0]
            remember(ws)
            ws_arg = w.ws_arg = ws.root  # every later step works on the backup that was found
            cfg = ws.config()
            if cfg.get("language") != chosen:
                cfg["language"] = chosen
                write_json(ws.config_path, cfg)
            report.update(ws, "config", report.config_md(cfg, ws.env_path))
            report.log(ws, "continued")
        else:
            if cli.init_from_answers(answers, ws_arg, quiet=True) != 0:
                return 1
            ws = resolve(ws_arg)
            w.say("ws_ready")
        w.path(ws.root)
        w.say("report_where")
        w.path(ws.report_path)

    if not read_token(ws)[0]:
        w.step(2, "t_token")
    if not token_step(w, ws):
        return 0

    w.step(3, "t_check")
    if not check_step(w, ws):
        print()
        w.say("doctor_fix")
        return 1

    phase = ws.state().get("phase")
    if not read_json(os.path.join(ws.station, "plan.json")) or phase == "interviewed":
        w.step(4, "t_scan")
        if not w.yes("scan_q"):
            return 0
        w.say("scanning")
        if cli.cmd_plan(_ns(ws_arg)) != 0:
            return 1
        w.say("found", summary=plan_summary(read_json(os.path.join(ws.station, "plan.json"))["totals"], w.lang))

    p, _ = pages.refresh(ws)
    if not pages.confirmed(ws, p):
        w.step(5, "t_pages")
        print(md_plain(pages.render(ws, w.lang)))
        if p["undecided_pages"] or not w.yes("pages_ok_q"):
            pages.ask_terminal(ws, inp, w.lang)
            p, _ = pages.refresh(ws)
            if p["undecided_pages"]:
                w.say("pages_undecided", n=p["undecided_pages"])
                return 1
            print(md_plain(pages.render(ws, w.lang)))
        pages.confirm(ws, p)
        report.update(ws, "pages", pages.render(ws))
        tot = p["totals"]
        w.say("pages_done", pages=tot["pages"], screens=tot["screens_est"], minutes=tot["minutes_est"])

    w.step(6, "t_backup")
    watched = None
    while True:
        if runner.running(ws):
            watched = watch(w, ws, p)
            if watched == "detached":
                w.say("watch_left")
                w.say("report_where")
                w.path(ws.report_path)
                return 0
        q, done, failed, _ = runner.progress(ws, p)
        st = ws.state()
        phase = st.get("phase")
        if phase in ("exported", "closed") and len(done) == len(q):
            break  # every file is backed up
        if watched == "paused" and "request" in (st.get("note") or ""):
            w.say("paused")  # the person pressed P
            return 0
        if phase == "exported" and failed:
            if not w.yes("retry_failed_q", n=len(failed)):
                break
        else:
            if done:
                show_progress(w, ws, p)
            if not w.yes("run_continue_q" if done or phase in ("paused", "running") else "run_start_q"):
                return 0
        rc = cli.cmd_run(_ns(ws_arg))
        if rc != 0:
            return rc

    cfg = ws.config()
    phase = ws.state().get("phase")
    if phase == "exported":
        if w.yes("close_q"):
            cli.cmd_close(_ns(ws_arg))
    elif w.yes("drift_q", default=False):
        cli.cmd_close(_ns(ws_arg))
        drift = read_json(os.path.join(ws.station, "drift.json"), {"files": {}})
        if any(v.get("edited_after") for v in drift.get("files", {}).values()):
            cli.cmd_refresh(_ns(ws_arg))
            if w.yes("rerun_q"):
                return cli.cmd_run(_ns(ws_arg))

    if ws.state().get("phase") == "closed":
        print()
        w.say("ready")
        w.path(ws.backup)
        cov = os.path.join(ws.backup, "COVERAGE.html")
        if os.path.exists(cov) and w.yes("coverage_q2"):
            w.open_page(cov)
        if w.yes("folder_q", default=False):
            w.open_folder(ws.backup)
    if cfg.get("local_copies") != "skip":
        w.say("copies")
        w.path(guide("local-copies.md"))
    w.say("report_where")
    w.path(ws.report_path)
    return 0


def _open(path):
    import pathlib
    import webbrowser
    webbrowser.open(pathlib.Path(path).resolve().as_uri())


def _open_folder(path):
    """Show a folder in Explorer, Finder or the desktop's file manager."""
    system = platform.system()
    if system == "Windows":
        os.startfile(path)  # noqa: S606 - a folder the kit made
    else:
        subprocess.Popen(["open" if system == "Darwin" else "xdg-open", path])


def _open_in_editor(path):
    """Open a text file in the system's plain editor: Notepad, TextEdit, or whatever opens text files."""
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["notepad.exe", path])
    elif system == "Darwin":
        subprocess.Popen(["open", "-e", path])
    else:
        subprocess.Popen(["xdg-open", path])
