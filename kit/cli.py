"""Command line: start · doctor · questions · init · plan · pages · run · resume · stop · status and the add-ons."""
import argparse
import getpass
import json
import os
import sys
import time

from . import VERSION, close, copies, doctor, gallery, handoff, interview, pages, plan, report, runner, start, tokens, variables
from .figapi import read_token
from .util import md_plain, now_iso, plural, read_json, size_text, utf8_console, write_json
from .workspace import Workspace, clean_token, remember, resolve, save_token



def cmd_doctor(a):
    ws = resolve(a.workspace)
    r = doctor.run(ws, ai=doctor.parse_ai(a.ai), network=not a.offline)
    md = doctor.render(r)
    if ws and ws.exists():
        report.update(ws, "doctor", doctor.render(r, report.lang_of(ws)))
    out = json.dumps(r, ensure_ascii=False, indent=1) if a.json else md
    print(doctor.redact(out, ws) if getattr(a, "redact", False) else out)
    return 0 if r["core_ready"] else 1


def cmd_questions(a):
    print(json.dumps(interview.QUESTIONS, ensure_ascii=False, indent=1) if a.json else interview.render_md())
    return 0


def cmd_init(a):
    if a.answers:
        if not os.path.exists(a.answers):
            print(f"{a.answers}: file not found")
            return 1
        answers = read_json(a.answers)
        if not isinstance(answers, dict):
            print(f"{a.answers}: expected a JSON object with the question ids as keys")
            return 1
    elif sys.stdin.isatty():
        answers = interview.ask_terminal()
    else:
        print("Give the answers with --answers <file.json> (see: python kit.py questions --json).")
        return 1
    return init_from_answers(answers, a.workspace, as_json=a.json, ask_token=sys.stdin.isatty() and not a.answers)


def init_from_answers(answers, workspace=None, as_json=False, ask_token=False, quiet=False):
    """Validate the answers, create the workspace and write config.json. Returns 0 or 1."""
    if workspace:
        answers["workspace"] = workspace
    target = Workspace(os.path.expanduser(answers.get("workspace") or interview.BY_ID["workspace"]["default"]))
    cfg, errors, warnings = interview.validate(answers, read_json(target.doctor_path))
    if as_json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                          "config": cfg if not errors else None}, ensure_ascii=False, indent=1))
    if errors:
        if not as_json:
            print("Some answers need fixing:\n" + "\n".join(f"  ✖ {e}" for e in errors))
        return 1

    ws = Workspace(cfg["workspace"])
    previous = ws.state().get("phase") if ws.exists() else None
    ws.create()
    write_json(ws.config_path, cfg)
    if previous in (None, "interviewed"):
        ws.set_phase("interviewed")
    remember(ws)
    report.update(ws, "config", report.config_md(cfg, ws.env_path))
    report.log(ws, "settings")

    if ask_token and not read_token(ws)[0]:
        print("\nPaste your Figma token now, or press Enter to add it later.")
        print("Paste with right-click or Ctrl+V (Cmd+V on a Mac). Nothing shows while you paste: that's normal.")
        tok = getpass.getpass("Token (hidden): ")
        if clean_token(tok):
            save_token(ws, tok)
            report.log(ws, "token")
            print("✔ Token saved in " + ws.env_path)
        else:
            print("No token yet. Paste it later after FIGMA_TOKEN= in " + ws.env_path)
    if not as_json and not quiet:
        for w in warnings:
            print(f"  ! {w}")
        print(f"Workspace ready: {ws.root}")
        print(f"Settings: {ws.config_path}")
        if previous not in (None, "interviewed"):
            print(f"  ! The job was already at '{previous}'. New settings apply from the next step.")
        print("Next: python kit.py doctor" if read_token(ws)[0] else
                  "Next: put your Figma token in " + ws.env_path + ", then run: python kit.py doctor")
    return 0


def _ready(a, need_plan=False):
    """Workspace + config + token (+ plan). Returns (ws, token, plan) or prints why not and returns None."""
    ws = resolve(a.workspace)
    if not ws or not ws.config():
        print("No workspace yet: run python kit.py init first.")
        return None
    token, _ = read_token(ws)
    if not token:
        print(f"No Figma token: paste it after FIGMA_TOKEN= in {ws.env_path}, then run python kit.py doctor.")
        return None
    p = read_json(os.path.join(ws.station, "plan.json"))
    if need_plan and not p:
        print("No plan yet: run python kit.py plan first.")
        return None
    return ws, token, p


def cmd_plan(a):
    r = _ready(a)
    if not r:
        return 1
    ws, token, _ = r
    if runner.running(ws):
        print("A run is in progress. Stop it first (python kit.py stop) or wait for it to pause.")
        return 1
    guided = getattr(a, "guided", False)
    if not guided:
        print("Scanning Figma (≈ 1.5 s per call)…")
    inv = plan.scan(ws, token, **({"log": lambda m: None} if guided else {}))
    p, sel = plan.build(ws, inv)
    report.update(ws, "plan", plan.render(p, sel, ws.config()))
    if ws.state().get("phase") in (None, "interviewed", "planned"):
        ws.set_phase("planned")
    report.update(ws, "pages", pages.render(ws))
    from .i18n import plan_summary as summary_in
    report.log(ws, "scanned", summary=summary_in(p["totals"], report.lang_of(ws)))
    if not guided:
        print(plan_summary(p))
        print(f"Details: {ws.report_path}")
        print("Next: choose the pages to back up: python kit.py pages")
    return 0


def plan_summary(p):
    t = p["totals"]
    return (f"{plural(t['files'], 'file')} in {plural(t['projects'], 'project')} · {plural(t['pages'], 'page')} · "
            f"≈ {plural(t['screens_est'], 'screen')} · ≈ {t['minutes_est']} min · "
            f"{size_text(t.get('mb_est', t['gb_est'] * 1024))}")


def cmd_pages(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws, _, p = r
    try:
        for spec in a.choose or []:
            ref, sep, nums = spec.rpartition("=")
            if not sep:
                raise ValueError(f"'{spec}': use <file>=<page numbers>, e.g. 1=1,3,5-7 or Onboarding=all")
            pages.choose(ws, ref, nums)
        if a.edit:
            if not sys.stdin.isatty():
                raise ValueError("--edit needs a terminal; use --choose <file>=<numbers> instead")
            pages.ask_terminal(ws)
    except ValueError as e:
        print(f"✖ {e}")
        return 1
    p, sel = pages.refresh(ws)  # no network: rebuilds plan.json from the saved scan and the page choices
    report.update(ws, "plan", plan.render(p, sel, ws.config()))
    report.update(ws, "pages", pages.render(ws))
    if a.confirm or a.edit:
        if p["undecided_pages"]:
            print(f"✖ {p['undecided_pages']} pages are still undecided: choose them first.")
            return 1
        pages.confirm(ws, p)
    if a.json:
        print(json.dumps([{"n": n, "key": k, "project": rec["project"], "file": rec["file"],
                           "pages": [{"n": i, "name": pg["name"], "export": pg["export"], "why": pg["why"], "screens_est": pg["est"]}
                                     for i, (_, pg) in enumerate(pl, 1)]}
                          for n, k, rec, pl in pages.files(ws)], ensure_ascii=False, indent=1))
        return 0
    print(pages.render(ws))
    t = p["totals"]
    print(f"Selected: {plural(t['pages'], 'page')} in {plural(t['files_with_pages'], 'file')} · "
          f"≈ {plural(t['screens_est'], 'screen')} · ≈ {t['minutes_est']} min")
    if pages.confirmed(ws, p):
        print("Confirmed. Next: python kit.py run")
    else:
        print("Change: python kit.py pages --choose <file>=<numbers>  (e.g. 1=1,3,5-7 · 1=all · 1=none)")
        print("Then confirm: python kit.py pages --confirm   (or walk through every file: --edit)")
    return 0


def cmd_run(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws, _, p = r
    if not pages.confirmed(ws, p):
        print("Confirm the pages to back up first: python kit.py pages (then --confirm).")
        return 1
    if runner.running(ws) and ws.state().get("pid") != os.getpid():  # the started run itself may go on
        print(f"Already running (process {ws.state().get('pid')}). Check with python kit.py status.")
        return 1
    if a.foreground:
        return runner.run(ws)
    pid = runner.start_detached(ws)
    ws.set_phase("running", pid=pid, started=now_iso())  # at once, so a watcher sees it before the run writes it
    report.log(ws, "run_start")
    if not getattr(a, "guided", False):
        print(f"Started in the background (process {pid}). It keeps going if you close this app.")
        print(f"Log: {os.path.join(ws.logs, 'run.log')} · progress: python kit.py status · pause: python kit.py stop")
    return 0


def cmd_copies(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws = r[0]
    if ws.config()["local_copies"] == "skip":
        print("Local copies are switched off in the settings (local_copies: skip). Run init again to switch them on.")
        return 1
    try:
        if a.action == "open":
            rec = copies.open_file(ws, a.ref or "", force=a.force)
            print(f"Opened {rec['name']} in Figma desktop.")
            print(f"Save it with: Quick actions (Ctrl+/ or Cmd+/) → Save local copy → {rec['target']}")
            print(f"Or save it to {copies.inboxes(ws)[0]} or Downloads: python kit.py copies check files it.")
        elif a.action == "skip":
            copies.skip(ws, a.ref or "", a.reason)
        elif a.action == "check":
            for rec in copies.check(ws):
                print(f"✔ {rec['name']} ({rec['size'] / 2**20:.1f} MB)")
        elif a.action == "watch":
            print("Watching for saved copies (Ctrl+C to stop)…")
            print("All opened files are saved." if copies.watch(ws, a.minutes) else "Time is up; some files are still open.")
        elif a.action == "next":
            data = copies.sync(ws)
            todo = [x for x in copies.ordered(data) if x["status"] in ("todo", "failed")]
            nxt = {"file": todo[0] if todo else None, "wait_seconds": copies.wait_seconds(data), "left": len(todo)}
            print(json.dumps(nxt, ensure_ascii=False, indent=1))
            return 0
    except ValueError as e:
        print(f"✖ {e}")
        return 1
    md = copies.render(ws)
    report.update(ws, "copies", md)
    if a.action == "list":
        print(json.dumps(copies.ordered(copies.sync(ws)), ensure_ascii=False, indent=1) if a.json else md)
    return 0


def cmd_close(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws, token, _ = r
    if runner.running(ws):
        print("A run is in progress: close when it has finished.")
        return 1
    cfg = ws.config()
    v = close.verify(ws)
    d = close.drift(ws, token) if cfg["addons"]["drift"] else None
    cov = close.coverage(ws) if cfg["addons"]["coverage"] else None
    arch = close.archives(ws) if cfg["addons"]["archives"] else None
    lang = report.lang_of(ws)
    report.update(ws, "close", close.render(v, d, arch, cov, lang))
    write_json(os.path.join(ws.station, "verify.json"), v)
    if ws.state().get("phase") == "exported" and not v["problems"]:
        ws.set_phase("closed", closed=v["checked"])
    report.log(ws, "closed", checked=v["totals"].get("files", 0), problems=len(v["problems"]))
    if getattr(a, "guided", False):  # Start: plain text, in the language its window can show
        print(md_plain(close.render(v, d, arch, cov, start.window_language(lang))))
    else:
        print(close.render(v, d, arch, cov))
    return 0 if not v["problems"] else 1


def cmd_refresh(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws = r[0]
    if runner.running(ws):
        print("A run is in progress: refresh when it has finished.")
        return 1
    names = close.refresh(ws)
    if not names:
        print("Nothing changed in Figma since the backup (per the last drift check: python kit.py close).")
        return 0
    report.log(ws, "refresh", names=", ".join(names))
    print(f"Queued again: {', '.join(names)}. Their old backup is in {os.path.join(ws.temp, 'replaced')}.")
    if getattr(a, "guided", False):
        return 0
    print("Next: python kit.py run" + (" · then the local copies again: python kit.py copies" if ws.config()["local_copies"] != "skip" else ""))
    return 0


def _design_files(ws):
    p = read_json(os.path.join(ws.station, "plan.json"))
    return [q for q in p["queue"] if q["editorType"] == "figma"]


def tokens_md(ws):
    lines = ["# Tokens", "", "| # | File | Variables | Token report |", "|---|---|---|---|"]
    for n, q in enumerate(_design_files(ws), 1):
        st = variables.status(ws, q)
        var = (f"{st['variables']} ({st['source']})" if st["variables"] else "native export only" if st["native"] else "—")
        sc = read_json(os.path.join(ws.station, "screens", q["key"] + ".json"))
        u = read_json(tokens.usage_path(ws, sc)) if sc else None
        s = u.get("summary") if u else None
        rep = (f"{s['screens']} screens · {s['token_svgs']} token SVGs · {s['raw_is_token_svg']} need none · "
               f"{s['screens_with_unbound_colors']} with unbound colours"
               + (f" · {s['unresolved_variables']} use library variables not in the backup" if s.get("unresolved_variables") else "")) if s else "—"
        lines.append(f"| {n} | {q['name']} | {var} | {rep} |")
    return "\n".join(lines) + "\n"


def cmd_tokens(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws, token, _ = r
    files = _design_files(ws)
    try:
        if a.action == "script":
            with open(variables.SCRIPT, encoding="utf-8") as f:
                print(f.read())
            return 0
        if a.action == "vars":
            pick = [pages.find_file(ws, a.ref)[0]] if a.ref else [q["key"] for q in files]
            for q in [x for x in files if x["key"] in pick]:
                d = variables.from_rest(ws, q, token)
                print(f"{'✔' if d else '–'} {q['name']}: " + (f"{len(d['meta']['variables'])} variables (REST)" if d
                      else "no variables by REST (none in this file, or not an Enterprise plan)"))
            print("Files without REST access: use Figma's MCP (python kit.py tokens script) or the native export "
                  "(Variables panel → right-click a collection → Export modes), then python kit.py tokens import <file> <path>.")
        elif a.action == "import":
            if not a.ref or not a.path:
                raise ValueError("use: python kit.py tokens import <file> <path to .json, .zip or folder>")
            key = pages.find_file(ws, a.ref)[0]
            q = next(x for x in files if x["key"] == key)
            src, n = variables.import_path(ws, q, a.path)
            print(f"✔ {q['name']}: {n} {'variables' if src == 'mcp' else 'native token files'} imported ({src})")
        elif a.action == "svgs":
            if a.background and not a.foreground:
                pid = runner.start_detached(ws, ("tokens", "svgs"), "tokens.log")
                print(f"Started in the background (process {pid}). Log: {os.path.join(ws.logs, 'tokens.log')}")
                return 0
            VARS = variables.load_all(ws, files)
            if not VARS:
                raise ValueError("no variables saved yet: python kit.py tokens vars (or tokens import) first")
            st = ws.state().get("files", {})
            for q in files:
                if st.get(q["key"], {}).get("status") != "done":
                    continue
                print(f"→ {q['name']}")
                res = tokens.run_file(ws, q, VARS, token)
                if "changed" in res:
                    print(f"  changed in Figma since the backup ({res['changed']}): python kit.py refresh, then run, first")
                    continue
                gallery.build(ws, read_json(os.path.join(ws.station, "screens", q["key"] + ".json")))
                print(f"  ✔ {res['token_svgs']} token SVGs · {res['raw_is_token_svg']} need none · "
                      f"{res['colors_tokenized']} colours tokenized")
                if res.get("unresolved_variables"):
                    print(f"  ! {res['unresolved_variables']} screens use variables from a library file that isn't in this "
                          "backup: add that file's link to the backup and import its variables, then run tokens svgs again")
    except ValueError as e:
        print(f"✖ {e}")
        return 1
    md = tokens_md(ws)
    report.update(ws, "tokens", md)
    if a.action == "list":
        print(md)
    return 0


def cmd_handoff(a):
    r = _ready(a, need_plan=True)
    if not r:
        return 1
    ws, token, _ = r
    try:
        key, plist = pages.find_file(ws, a.ref or "")
        nums = pages.parse_numbers(a.pages or "", len(plist))
        if not nums:
            raise ValueError("choose the pages with --pages, e.g. --pages 2 or --pages 1,3-4 (numbers from python kit.py pages)")
    except ValueError as e:
        print(f"✖ {e}")
        return 1
    item = next(q for q in _design_files(ws) if q["key"] == key)
    name = a.name or f"{item['name']} - handoff {time.strftime('%Y-%m-%d')}"
    if a.background and not a.foreground:
        pid = runner.start_detached(ws, ("handoff", a.ref, "--pages", a.pages, "--name", name), "handoff.log")
        print(f"Started in the background (process {pid}). Log: {os.path.join(ws.logs, 'handoff.log')}")
        return 0
    base, res = handoff.run(ws, item, [plist[i - 1][0] for i in sorted(nums)], name, token)
    print(f"Handoff ready: {os.path.join(base, 'index.html')}")
    for k, v in res.items():
        print(f"  {k}: {v}")
    return 0


def cmd_stop(a):
    ws = resolve(a.workspace)
    if not ws or not runner.running(ws):
        print("Nothing is running.")
        return 0
    runner.request_stop(ws)
    report.log(ws, "stop")
    if getattr(a, "guided", False):
        return 0
    print("Asked the run to pause after the current batch of screens. python kit.py resume continues it.")
    return 0


def cmd_status(a):
    ws = resolve(a.workspace)
    if not ws or not ws.exists():
        print("No workspace yet. Start with: python kit.py doctor, then python kit.py questions / init.")
        return 1
    cfg, st, doc = ws.config(), ws.state(), read_json(ws.doctor_path, {})
    p = read_json(os.path.join(ws.station, "plan.json"))
    out = {"workspace": ws.root, "phase": st.get("phase"), "note": st.get("note"), "updated": st.get("updated"),
           "running": runner.running(ws), "mode": (cfg or {}).get("mode"),
           "doctor_checked": doc.get("checked"), "core_ready": doc.get("core_ready"), "report": ws.report_path}
    if p:
        q, done, failed, files = runner.progress(ws, p)
        out.update(files=len(q), done=len(done), failed=len(failed),
                   screens=sum(files[x["key"]].get("screens", 0) for x in done),
                   current=next((x["name"] for x in q if files.get(x["key"], {}).get("status") == "running"), None))
    logp = os.path.join(ws.logs, "run.log")
    if os.path.exists(logp):
        with open(logp, encoding="utf-8", errors="replace") as f:
            out["log_tail"] = [ln.rstrip() for ln in f.readlines()[-3:]]
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print(f"Workspace: {ws.root}")
    phase = out["phase"] + (" (process alive)" if out["running"] else " (process gone: resume to continue)"
                            if out["phase"] == "running" else "")
    print(f"Phase:     {phase}" + (f" · {out['note']}" if out.get("note") and out["phase"] == "paused" else ""))
    print(f"Mode:      {out['mode']}")
    if p:
        print(f"Progress:  {out['done']} / {out['files']} files · {out['screens']} screens"
              + (f" · {out['failed']} failed" if out["failed"] else "")
              + (f" · now: {out['current']}" if out["current"] and out["running"] else ""))
    print(f"Doctor:    {'ready' if doc.get('core_ready') else 'not ready'} (checked {doc.get('checked')})" if doc
          else "Doctor:    not run yet")
    for ln in out.get("log_tail", []):
        print(f"  log │ {ln}")
    print(f"Report:    {ws.report_path}")
    return 0


def cmd_start(a):
    from .i18n import t
    lang = a.lang
    try:
        return start.run(a.workspace, lang=lang)
    except (KeyboardInterrupt, EOFError):
        ws = resolve(a.workspace)
        lang = lang or ((ws.config() if ws else None) or {}).get("language", "en")
        print("\n" + t("stopped", lang))
        return 1
    finally:
        if os.environ.get("FOK_PAUSE") and sys.stdin.isatty():
            try:
                input("\n" + t("press_enter", lang or "en") + " ")
            except (KeyboardInterrupt, EOFError):
                pass


def main(argv=None):
    utf8_console()
    p = argparse.ArgumentParser(prog="kit.py", description=f"figma-offline-kit {VERSION}: back up a Figma team for offline work.")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        s = sub.add_parser(name, help=help_)
        s.add_argument("--workspace", help="workspace folder (default: the one from the last init)")
        s.add_argument("--json", action="store_true", help="machine-readable output")
        s.set_defaults(fn=fn)
        return s

    add("start", cmd_start, "guided start: walks you through every step (what Start.bat / Start.command run)").add_argument(
        "--lang", choices=["fa", "en"], help="language of the guided start (fa = Persian); asked first if not given")
    d = add("doctor", cmd_doctor, "check the machine, token and tools")
    d.add_argument("--ai", default="", help="what the AI can do, e.g. desktop-control=yes,figma-mcp=no")
    d.add_argument("--offline", action="store_true", help="skip network checks")
    d.add_argument("--redact", action="store_true", help="hide your folders and Figma name, for sharing in an issue")
    add("questions", cmd_questions, "print the interview questions")
    add("init", cmd_init, "answer the interview and create the workspace").add_argument(
        "--answers", help="JSON file with the answers (keys = question ids)")
    add("plan", cmd_plan, "scan the team and plan the work")
    pg = add("pages", cmd_pages, "show and choose the pages to back up")
    pg.add_argument("--choose", action="append", metavar="FILE=PAGES",
                    help="set the pages of one file, e.g. 1=1,3,5-7 or Onboarding=all (repeatable)")
    pg.add_argument("--edit", action="store_true", help="walk through every file in the terminal")
    pg.add_argument("--confirm", action="store_true", help="confirm the current choice so the run can start")
    for name, help_ in (("run", "export everything in the plan (in the background)"),
                        ("resume", "continue a paused or interrupted run")):
        add(name, cmd_run, help_).add_argument("--foreground", action="store_true", help="run in this console")
    cp = add("copies", cmd_copies, "local .fig/.jam/.deck copies from Figma desktop")
    cp.add_argument("action", nargs="?", default="list", choices=["list", "next", "open", "check", "watch", "skip"])
    cp.add_argument("ref", nargs="?", help="file number, name or key (open, skip)")
    cp.add_argument("--force", action="store_true", help="open even if pacing says wait")
    cp.add_argument("--reason", default="", help="why the file is skipped (skip)")
    cp.add_argument("--minutes", type=float, default=30, help="how long to watch (watch)")
    tk = add("tokens", cmd_tokens, "design-token add-on: variables, CSS/SCSS, token SVGs")
    tk.add_argument("action", nargs="?", default="list", choices=["list", "vars", "script", "import", "svgs"])
    tk.add_argument("ref", nargs="?", help="design file number, name or key (vars, import)")
    tk.add_argument("path", nargs="?", help="saved MCP JSON, native export zip or folder (import)")
    tk.add_argument("--background", action="store_true", help="svgs: run in the background")
    tk.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)
    ho = add("handoff", cmd_handoff, "dev handoff package for chosen pages (code, specs, tokens)")
    ho.add_argument("ref", nargs="?", help="design file number, name or key (as in python kit.py pages)")
    ho.add_argument("--pages", help="page numbers from python kit.py pages, e.g. 2 or 1,3-4")
    ho.add_argument("--name", help="folder name under <workspace>/handoff/")
    ho.add_argument("--background", action="store_true", help="run in the background")
    ho.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)
    add("stop", cmd_stop, "pause a running export")
    add("close", cmd_close, "verify, drift check, coverage page, archives")
    add("refresh", cmd_refresh, "re-queue files that changed in Figma since the backup")
    add("status", cmd_status, "where the job stands")
    a = p.parse_args(argv)
    return a.fn(a)
