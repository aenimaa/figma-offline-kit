"""Guided start: one terminal window that walks a person through the whole backup, step by step.

`python kit.py start`, or double-click start.bat (Windows) / start.command (macOS, Linux). It picks up where
the job stands, so running it again shows progress or offers the next step."""
import argparse
import os

from . import pages, report, runner
from .figapi import read_token
from .util import read_json
from .workspace import resolve

STEPS = 5


def _ns(ws_arg, **kw):
    d = dict(workspace=ws_arg, json=False, ai="", offline=False, answers=None, choose=None, edit=False,
             confirm=False, foreground=False)
    d.update(kw)
    return argparse.Namespace(**d)


def _yes(question, inp, default=True):
    while True:
        raw = inp(f"{question} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False


def _step(n, title):
    print(f"\n── Step {n} of {STEPS} · {title} " + "─" * max(0, 40 - len(title)))


def _plan(ws):
    return read_json(os.path.join(ws.station, "plan.json"))


def run(ws_arg=None, inp=input, open_page=None):
    from . import cli  # late import: cli imports this module

    print("figma-offline-kit · guided start")
    print("Answer each question, or press Enter for the suggestion in [brackets]. Ctrl+C stops at any time.")
    ws = resolve(ws_arg)

    if not ws or not ws.config():
        _step(1, "Setup")
        print("A few questions: your Figma team or file links, where to save the backup, and how to run it.")
        if cli.cmd_init(_ns(ws_arg)) != 0:
            return 1
        ws = resolve(ws_arg)

    while not read_token(ws)[0]:
        print("\nThe kit needs a read-only Figma token. How to make one: docs/figma-token.md")
        print(f"Open this file in a text editor and paste the token after FIGMA_TOKEN=\n  {ws.env_path}")
        if not _yes("Done? Check again", inp):
            print("Start again when the token is in place.")
            return 0

    _step(2, "Check")
    if cli.cmd_doctor(_ns(ws_arg)) != 0:
        print("\nFix the items under “You need to do” above, then start again.")
        return 1

    phase = ws.state().get("phase")
    if not _plan(ws) or phase == "interviewed":
        _step(3, "Scan Figma")
        if not _yes("Scan Figma now to see what's there? It only reads", inp):
            return 0
        if cli.cmd_plan(_ns(ws_arg)) != 0:
            return 1

    p, _ = pages.refresh(ws)
    if not pages.confirmed(ws, p):
        _step(4, "Pages")
        print(pages.render(ws))
        if p["undecided_pages"] or not _yes("Back up the pages marked ✔? (n = choose file by file)", inp):
            pages.ask_terminal(ws, inp)
            p, sel = pages.refresh(ws)
            if p["undecided_pages"]:
                print(f"✖ {p['undecided_pages']} pages are still undecided. Start again to choose them.")
                return 1
            print(pages.render(ws))
        pages.confirm(ws, p)
        report.update(ws, "pages", pages.render(ws))
        t = p["totals"]
        print(f"Confirmed: {t['pages']} pages · ≈ {t['screens_est']} screens · ≈ {t['minutes_est']} min")

    _step(5, "Backup")
    if runner.running(ws):
        cli.cmd_status(_ns(ws_arg))
        print("\nThe backup is running in the background. You can close this window;"
              " start again any time to see progress.")
        return 0

    q, done, failed, _ = runner.progress(ws, p)
    phase = ws.state().get("phase")
    if phase not in ("exported", "closed") or len(done) < len(q):
        what = "Continue the backup" if done or phase in ("paused", "running") else "Start the backup"
        if _yes(f"{what} now? It runs in the background and keeps going if you close this window", inp):
            return cli.cmd_run(_ns(ws_arg))
        return 0

    cfg = ws.config()
    if phase == "exported":
        if _yes("All screens are exported. Check everything and pack the archives now?", inp):
            cli.cmd_close(_ns(ws_arg))
    elif _yes("Look for files that changed in Figma since the backup?", inp, default=False):
        cli.cmd_close(_ns(ws_arg))
        drift = read_json(os.path.join(ws.station, "drift.json"), {"files": {}})
        if any(v.get("edited_after") for v in drift.get("files", {}).values()):
            cli.cmd_refresh(_ns(ws_arg))
            if _yes("Export the changed files again now?", inp):
                return cli.cmd_run(_ns(ws_arg))

    if ws.state().get("phase") == "closed":
        print(f"\nYour backup is ready in {ws.backup}")
        cov = os.path.join(ws.backup, "COVERAGE.html")
        if os.path.exists(cov) and _yes("Open the coverage page?", inp):
            (open_page or _open)(cov)
    if cfg.get("local_copies") != "skip":
        print("Local .fig copies are a separate step with Figma desktop: python kit.py copies (see docs/local-copies.md).")
    return 0


def _open(path):
    import pathlib
    import webbrowser
    webbrowser.open(pathlib.Path(path).resolve().as_uri())
