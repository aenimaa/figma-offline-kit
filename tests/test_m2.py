"""M2 tests: plan → run → gallery end to end against the fake Figma server (tests/fake_figma.py)."""
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from contextlib import redirect_stdout

from kit import figapi, interview, plan, report, runner
from kit.export import screens_path, target
from kit.util import write_json, write_text
from kit.workspace import Workspace
from tests import fake_figma

QUIET = lambda *a, **k: None  # noqa: E731


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def load(p):
    return json.loads(read(p))


def make_ws(root, base, **answers):
    a = {"workspace": root, "team": f"https://www.figma.com/files/team/{fake_figma.TEAM_ID}/Example-Team",
         "mode": "full", "local_copies": "skip"}
    a.update(answers)
    cfg, errors, _ = interview.validate(a)
    assert not errors, errors
    ws = Workspace(cfg["workspace"])
    ws.create()
    write_json(ws.config_path, cfg)
    ws.set_phase("interviewed")
    write_text(ws.env_path, f"FIGMA_TOKEN={fake_figma.TOKEN}\n")
    return ws


def do_plan(ws):
    inv = plan.scan(ws, fake_figma.TOKEN, log=QUIET)
    p, sel = plan.build(ws, inv)
    report.update(ws, "plan", plan.render(p, sel, ws.config()))
    return p, sel


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP)
        figapi.API, figapi.MIN_GAP = cls.base, 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plan_applies_page_rule(self):
        ws = make_ws(self.tmp, self.base)
        p, sel = do_plan(ws)
        pages = {v["name"]: (v["export"], v["why"]) for v in sel["FAKEkeyAAA1"]["pages"].values()}
        self.assertEqual(pages["Cover"], (True, "rule"))
        self.assertEqual(pages["-------"], (False, "divider"))
        self.assertEqual(pages["Archive v1"], (False, "archive"))
        self.assertNotIn("FAKEkeyBBB2", sel)  # FigJam: no screen export
        t = p["totals"]
        self.assertEqual((t["projects"], t["files"], t["design_files"], t["pages"]), (2, 3, 2, 3))

    def test_user_page_choice_survives_replan(self):
        ws = make_ws(self.tmp, self.base)
        _, sel = do_plan(ws)
        sel["FAKEkeyAAA1"]["pages"]["0:4"]["export"] = True
        write_json(os.path.join(ws.station, "pages.json"), sel)
        _, sel = do_plan(ws)
        self.assertEqual(sel["FAKEkeyAAA1"]["pages"]["0:4"]["export"], True)
        self.assertEqual(sel["FAKEkeyAAA1"]["pages"]["0:4"]["why"], "you")

    def test_pick_rule_blocks_until_decided(self):
        ws = make_ws(self.tmp, self.base, pages="pick")
        p, _ = do_plan(ws)
        self.assertEqual(p["undecided_pages"], 4)  # dividers are decided: never exported

    def test_full_run(self):
        ws = make_ws(self.tmp, self.base)
        do_plan(ws)
        self.assertEqual(runner.run(ws, log=QUIET), 0)
        st = ws.state()
        self.assertEqual(st["phase"], "exported")
        self.assertEqual({k: v["status"] for k, v in st["files"].items()}, {"FAKEkeyAAA1": "done", "FAKEkeyCCC3": "done"})

        a = load(screens_path(ws, "FAKEkeyAAA1"))
        names = [s["name"] for s in a["screens"]]
        self.assertEqual(sorted(names), sorted(["Cover", "Welcome", "Email", "Email taken", "Home", "Icons"]))
        taken = next(s for s in a["screens"] if s["name"] == "Email taken")
        self.assertEqual(taken["section"], "Sign up / Errors")
        for s in a["screens"]:
            for ext in ("png", "svg"):
                self.assertTrue(os.path.exists(target(ws, a, s, ext)), (s["name"], ext))

        c = load(screens_path(ws, "FAKEkeyCCC3"))
        by = {s["name"]: s for s in c["screens"]}
        self.assertLess(by["Landing long"]["scale"], 2)
        self.assertTrue(os.path.exists(target(ws, c, by["Hero video"], "pdf")))
        self.assertFalse(os.path.exists(target(ws, c, by["Hero video"], "svg")))
        self.assertEqual(st["files"]["FAKEkeyCCC3"]["empty"], 1)

        idx = os.path.join(ws.backup, "Mobile App", "Onboarding", "index.html")
        html = read(idx)
        self.assertNotIn("@@", html)
        self.assertIn('"name":"Email taken"', html)
        self.assertIn("Project: <span dir=\"auto\">Mobile App</span>", html)
        rep = read(ws.report_path)
        self.assertIn("## Plan", rep)
        self.assertIn("**2 / 2 files** done", rep)

        # resume after the end: nothing new, numbering unchanged
        before = {s["id"]: s["n"] for s in a["screens"]}
        n_calls = len(fake_figma.Handler.calls)
        runner.run(ws, log=QUIET)
        self.assertEqual(len(fake_figma.Handler.calls), n_calls)
        a2 = load(screens_path(ws, "FAKEkeyAAA1"))
        self.assertEqual({s["id"]: s["n"] for s in a2["screens"]}, before)

    def test_project_mode_pauses_between_projects(self):
        ws = make_ws(self.tmp, self.base, mode="project")
        do_plan(ws)
        runner.run(ws, log=QUIET)
        st = ws.state()
        self.assertEqual(st["phase"], "paused")
        self.assertEqual(st["files"]["FAKEkeyAAA1"]["status"], "done")
        self.assertNotIn("FAKEkeyCCC3", st["files"])
        runner.run(ws, log=QUIET)
        self.assertEqual(ws.state()["phase"], "exported")

    def test_stop_pauses_and_resume_finishes(self):
        ws = make_ws(self.tmp, self.base)
        do_plan(ws)

        def log(msg):
            if "→ Mobile App / Onboarding" in msg:
                runner.request_stop(ws)
        runner.run(ws, log=log)
        st = ws.state()
        self.assertEqual(st["phase"], "paused")
        self.assertEqual(st["files"]["FAKEkeyAAA1"]["status"], "waiting")
        runner.run(ws, log=QUIET)
        self.assertEqual(ws.state()["phase"], "exported")

    def test_png_only(self):
        ws = make_ws(self.tmp, self.base, formats=["png"])
        do_plan(ws)
        runner.run(ws, log=QUIET)
        c = load(screens_path(ws, "FAKEkeyCCC3"))
        self.assertFalse(any(os.path.exists(target(ws, c, s, "svg")) for s in c["screens"]))
        self.assertEqual(ws.state()["files"]["FAKEkeyCCC3"]["empty"], 0)  # no SVG pass → nothing judged empty

    def test_detached_run_survives_and_finishes(self):
        ws = make_ws(self.tmp, self.base)
        p, _ = do_plan(ws)
        from kit import pages
        pages.confirm(ws, p)
        env = {"FIGMA_KIT_API": self.base, "FIGMA_KIT_MIN_GAP": "0"}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            pid = runner.start_detached(ws)
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertTrue(pid)
        deadline = time.time() + 90
        while time.time() < deadline and ws.state().get("phase") != "exported":
            time.sleep(0.5)
        log = read(os.path.join(ws.logs, "run.log"))
        self.assertEqual(ws.state().get("phase"), "exported", log[-800:])
        for _ in range(20):  # the process ends right after writing its last state
            if not runner.pid_alive(pid):
                break
            time.sleep(0.25)
        self.assertFalse(runner.pid_alive(pid))
        self.assertFalse(runner.running(ws))


class Cli(unittest.TestCase):
    def test_run_without_workspace_explains(self):
        tmp = tempfile.mkdtemp()
        try:
            from kit import cli
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["run", "--workspace", os.path.join(tmp, "nothing")])
            self.assertEqual(rc, 1)
            self.assertIn("init", buf.getvalue())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class PageStep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP)
        figapi.API, figapi.MIN_GAP = cls.base, 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cli(self, *args):
        from kit import cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(list(args) + ["--workspace", self.tmp])
        return rc, buf.getvalue()

    def test_choose_confirm_and_run_gate(self):
        from kit import pages
        ws = make_ws(self.tmp, self.base)
        do_plan(ws)
        rc, out = self.cli("run", "--foreground")
        self.assertEqual(rc, 1)
        self.assertIn("Confirm the pages", out)
        rc, out = self.cli("pages", "--choose", "Onboarding=3-4", "--choose", "2=none", "--confirm")
        self.assertEqual(rc, 0, out)
        sel = {k: {v["name"]: v["export"] for v in r["pages"].values()} for k, r in load(os.path.join(ws.station, "pages.json")).items()}
        self.assertEqual(sel["FAKEkeyAAA1"], {"Cover": False, "-------": False, "Screens": True, "Archive v1": True})
        self.assertEqual(sel["FAKEkeyCCC3"], {"Desktop": False})
        self.assertIn("Confirmed", out)
        p = load(os.path.join(ws.station, "plan.json"))
        self.assertTrue(pages.confirmed(ws, p))
        # choices survive a fresh plan, and the confirmation still matches
        do_plan(ws)
        self.assertTrue(pages.confirmed(ws, load(os.path.join(ws.station, "plan.json"))))
        # a new change needs a new confirmation
        self.cli("pages", "--choose", "1=all")
        self.assertFalse(pages.confirmed(ws, load(os.path.join(ws.station, "plan.json"))))

    def test_bad_choice_explains(self):
        ws = make_ws(self.tmp, self.base)
        do_plan(ws)
        for spec, msg in (("9=1", "no design file"), ("1=7", "outside 1-4"), ("Onboarding", "<file>=<page numbers>")):
            rc, out = self.cli("pages", "--choose", spec)
            self.assertEqual(rc, 1)
            self.assertIn(msg, out)

    def test_terminal_walkthrough(self):
        from kit import pages
        ws = make_ws(self.tmp, self.base, pages="pick")
        do_plan(ws)
        replies = iter(["", "1,3", "none"])  # Enter on undecided pages is refused
        with redirect_stdout(io.StringIO()):
            pages.ask_terminal(ws, inp=lambda _: next(replies))
        p, _ = pages.refresh(ws)
        self.assertEqual(p["undecided_pages"], 0)
        self.assertEqual(p["totals"]["pages"], 2)

    def test_file_links_instead_of_team(self):
        link = "https://www.figma.com/design/FAKEkeyCCC3/Landing?node-id=1-0"
        ws = make_ws(self.tmp, self.base, team=link)
        self.assertEqual(ws.config()["files"], ["FAKEkeyCCC3"])
        p, sel = do_plan(ws)
        self.assertEqual([q["name"] for q in p["queue"]], ["Landing"])
        self.assertEqual(p["queue"][0]["project"], "Website")  # folder name from /meta
        runner.run(ws, log=QUIET)
        self.assertEqual(ws.state()["files"]["FAKEkeyCCC3"]["status"], "done")
