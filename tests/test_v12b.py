"""1.2 tests, second part: findings from the first no-AI test run (wrapping, defaults, ZIP view, token file,
plain checklist, no command hints, sizes and plurals) and the report at the top of the workspace with its log."""
import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import zipfile
from contextlib import redirect_stdout

from kit import cli, figapi, i18n, interview, report, runner, start
from kit.workspace import TOKEN_FILE_TEMPLATE, Workspace, take_token_file
from tests import fake_figma
from tests.test_m2 import make_ws
from tests.test_v12 import feed
from tools import build_downloads


class Interview(unittest.TestCase):
    def ask(self, *answers, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            a = interview.ask_terminal(feed(*answers), **kw)
        return a, buf.getvalue()

    def test_person_defaults_and_wording(self):
        a, out = self.ask("~/fb", "https://www.figma.com/files/team/1/x", *[""] * 9, person=True)
        self.assertEqual(a["mode"], "full")
        self.assertEqual(a["local_copies"], "skip")
        section = out[out.index("Also save real .fig copies"):]
        self.assertNotIn("AI", section[:section.index(">")])

    def test_ai_defaults_unchanged(self):
        a, _ = self.ask("~/fb", "https://www.figma.com/files/team/1/x", *[""] * 9)
        self.assertEqual((a["mode"], a["local_copies"]), ("project", "auto"))

    def test_lines_fit_the_console(self):
        _, out = self.ask("~/fb", "https://www.figma.com/files/team/1/x", *[""] * 9, person=True)
        _, out_fa = self.ask("~/fb", "https://www.figma.com/files/team/1/x", *[""] * 9, person=True, lang="fa")
        for line in (out + out_fa).splitlines():
            if not line.startswith(">"):
                self.assertLessEqual(len(line), 76, line)

    def test_wrong_option_asks_again(self):
        a, out = self.ask("~/fb", "https://www.figma.com/files/team/1/x", "9", "x", "1", *[""] * 8)
        self.assertEqual(a["mode"], "full")
        self.assertEqual(out.count("1–3"), 2)


class Small(unittest.TestCase):
    def test_summary_sizes_and_plurals(self):
        t = {"files": 1, "projects": 1, "pages": 1, "screens_est": 37, "minutes_est": 4, "mb_est": 24, "gb_est": 0.0}
        self.assertEqual(i18n.plan_summary(t), "1 file in 1 project · 1 page · ≈ 37 screens · ≈ 4 min · ≈ 24 MB")
        t.update(files=3, projects=2, pages=5, mb_est=2048)
        self.assertEqual(i18n.plan_summary(t), "3 files in 2 projects · 5 pages · ≈ 37 screens · ≈ 4 min · ≈ 2.0 GB")
        self.assertIn("مگابایت", i18n.plan_summary(dict(t, mb_est=24), "fa"))

    def test_inside_zip(self):
        self.assertTrue(start.inside_zip(os.path.join("C:" + os.sep, "Temp", "Temp1_figma-offline-kit-windows.zip", "app")))
        self.assertFalse(start.inside_zip(os.path.join("C:" + os.sep, "Users", "me", "figma-offline-kit-windows", "app")))
        saved = start.inside_zip
        start.inside_zip = lambda path=None: True
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(start.run(inp=feed()), 1)
            self.assertIn("Extract the ZIP first", buf.getvalue())
        finally:
            start.inside_zip = saved

    @unittest.skipUnless(os.name == "nt", "Windows start file")
    def test_start_bat_refuses_inside_zip_folder(self):
        tmp = tempfile.mkdtemp()
        try:
            (z,) = [p for p in build_downloads.build(tmp) if p.endswith("windows.zip")]
            dest = os.path.join(tmp, "Temp1_figma-offline-kit-windows.zip")
            with zipfile.ZipFile(z) as f:
                f.extractall(dest)
            r = subprocess.run(["cmd", "/c", os.path.join(dest, "Start.bat")], input="\n", capture_output=True,
                               text=True, timeout=60)
            self.assertIn("Extract the ZIP first", r.stdout)
            self.assertNotIn("guided start", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Guided(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL)
        figapi.API, figapi.MIN_GAP = cls.base, 0
        start.RTL_TERMINAL = False

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wizard(self, ws, *answers, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = start.run(ws.root, inp=feed(*answers), **kw)
        return rc, buf.getvalue()

    def test_token_file_next_to_start(self):
        ws = make_ws(self.tmp, self.base)
        with open(ws.env_path, "w", encoding="utf-8") as f:
            f.write("FIGMA_TOKEN=\n")
        drop = os.path.join(self.tmp, "Figma token.txt")
        with open(drop, "w", encoding="utf-8-sig") as f:  # Notepad may add a BOM
            f.write(TOKEN_FILE_TEMPLATE + f"\n  {fake_figma.TOKEN}  \n")
        w = start.Wizard(ws.root, feed(), "en", None, None, None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertTrue(start.token_step(w, ws, drop=drop))
        out = buf.getvalue()
        self.assertIn("Token taken from “Figma token.txt”", out)
        self.assertIn(ws.env_path, out)
        self.assertNotIn(fake_figma.TOKEN, out)
        with open(drop, encoding="utf-8") as f:
            self.assertEqual(f.read(), TOKEN_FILE_TEMPLATE)
        self.assertFalse(take_token_file(ws, drop))  # empty again: nothing to take

    def test_option_2_opens_the_visible_token_file(self):
        ws = make_ws(self.tmp, self.base)
        with open(ws.env_path, "w", encoding="utf-8") as f:
            f.write("FIGMA_TOKEN=\n")
        drop = os.path.join(self.tmp, "Figma token.txt")
        with open(drop, "w", encoding="utf-8") as f:
            f.write(TOKEN_FILE_TEMPLATE)
        opened = []

        def editor(path):
            opened.append(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(fake_figma.TOKEN + "\n")

        w = start.Wizard(ws.root, feed("2", ""), "en", None, editor, None)
        with redirect_stdout(io.StringIO()):
            self.assertTrue(start.token_step(w, ws, drop=drop))
        self.assertEqual(opened, [drop])

    def test_plain_checklist_and_no_command_hints(self):
        ws = make_ws(self.tmp, self.base)
        # scan: yes · pages as suggested: yes · start the backup: no
        rc, out = self.wizard(ws, "", "", "n", lang="en")
        self.assertEqual(rc, 0, out)
        check = out[out.index("Step 3 of 6"):out.index("Step 4 of 6")]
        self.assertNotIn("|", check)
        self.assertNotIn("##", check)
        self.assertNotIn("AI desktop control", check)
        self.assertIn("– Figma desktop MCP (optional, off)", check)
        self.assertIn("Ready. The backup can start.", check)
        self.assertIn("Found: ", out)
        self.assertNotIn("python kit.py", out)
        self.assertNotIn("0.0 GB", out)

    def test_report_at_the_top_with_log_and_decisions(self):
        ws = make_ws(self.tmp, self.base)
        self.assertEqual(ws.report_path, os.path.join(ws.root, "REPORT.md"))
        rc, out = self.wizard(ws, "", "", "n", lang="en")
        self.assertIn(ws.report_path, out)
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("## Settings: your decisions", text)
        self.assertIn("**How it runs:** all in one go, to the end", text)
        self.assertIn("## Log", text)
        self.assertIn("## Log\n\n- ", text)
        self.assertRegex(text, r"- \d{4}-\d\d-\d\d \d\d:\d\d · Pages confirmed: \d+ page\(s\) in \d+ file\(s\) \(you, in Start\)")
        self.assertIn("Check: ready (you, in Start)", text)
        self.assertNotIn(fake_figma.TOKEN, text)
        self.assertLess(text.index("## Log"), text.index("## Settings"))  # the log is near the top

    def test_settings_in_persian(self):
        ws = make_ws(self.tmp, self.base)
        self.wizard(ws, "n", lang="fa")  # scan: no
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("تنظیمات: تصمیم‌های شما", text)
        self.assertIn("زبان: فارسی", text)

    def test_old_report_moves_to_the_top(self):
        ws = Workspace(os.path.join(self.tmp, "old"))
        ws.create()
        with open(ws.old_report_path, "w", encoding="utf-8") as f:
            f.write("# Figma backup report\n\n<!-- kit:plan -->\n## Plan\n\nold plan\n<!-- /kit:plan -->\n")
        report.update(ws, "close", "# Close\n\nnew")
        self.assertFalse(os.path.exists(ws.old_report_path))
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("old plan", text)
        self.assertIn("## Close", text)

    def test_running_watch_keys_pause_and_retry(self):
        ws = make_ws(self.tmp, self.base)
        self.wizard(ws, "", "", "n", lang="en")
        stopped, keys = [], iter(["r", "p"])
        saved = (runner.running, runner.request_stop)
        runner.running = lambda w: not stopped
        runner.request_stop = lambda w: (stopped.append(w.root), w.set_phase("paused", note="stopped on request"))

        def poll(seconds):
            return next(keys, None)

        try:
            with open(runner.waiting_path(ws), "w", encoding="utf-8") as f:  # the run is waiting for Figma
                f.write('{"kind": "network", "until": %d}' % (time.time() + 60))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = start.run(ws.root, inp=feed(), lang="en", poll=poll)
            out = buf.getvalue()
        finally:
            runner.running, runner.request_stop = saved
        self.assertEqual(rc, 0, out)
        self.assertEqual(stopped, [ws.root])
        self.assertTrue(os.path.exists(runner.retry_path(ws)))  # R asked the run to retry now
        self.assertIn("Closing this window does NOT stop the backup", out)
        self.assertIn("Can't reach Figma: check your internet or VPN.", out)
        self.assertIn("Trying again in", out)
        self.assertIn("R = retry now", out)
        self.assertIn("Pausing after the current batch", out)
        self.assertIn("Double-click Start again", out)
        self.assertNotIn("python kit.py", out)

    def test_retry_file_wakes_a_wait(self):
        ws = make_ws(self.tmp, self.base)
        runner._hooks(ws)
        try:
            runner.request_retry(ws)
            t0 = time.time()
            figapi.nap(30, "network")
            self.assertLess(time.time() - t0, 3)
            self.assertFalse(os.path.exists(runner.retry_path(ws)))
            self.assertEqual(json.load(open(runner.waiting_path(ws), encoding="utf-8"))["kind"], "network")
        finally:
            figapi.WAIT_HOOK = figapi.RETRY_HOOK = None

    def test_guided_run_shows_live_progress_then_packs(self):
        ws = make_ws(self.tmp, self.base)
        env = {"FIGMA_KIT_API": self.base, "FIGMA_KIT_MIN_GAP": "0"}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                # scan · pages · start the backup: yes · (live view) · check and pack: yes · coverage: no · folder: no
                rc = start.run(ws.root, inp=feed("", "", "", "y", "n", "n"), lang="en",
                               poll=lambda s: (time.sleep(0.3), None)[1])
            out = buf.getvalue()
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(rc, 0, out)
        self.assertIn("Closing this window does NOT stop the backup", out)
        self.assertRegex(out, r"✔ Onboarding: \d+ screens")
        self.assertRegex(out, r"✔ Backup finished: \d+ screens, 0 failed")
        self.assertIn("Problems: 0", out)
        self.assertEqual(ws.state()["phase"], "closed")
        self.assertNotIn("python kit.py", out)
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Backup started (you, in Start)", text)
        self.assertRegex(text, r"Backup finished: \d+ screens, 0 failed \(the kit, in the background\)")


class Batch3(unittest.TestCase):
    """Findings 12–16: estimate, short re-check, plain close, end offers."""
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL)
        figapi.API, figapi.MIN_GAP = cls.base, 0
        start.RTL_TERMINAL = False

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wizard(self, ws, *answers, opened=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = start.run(ws.root, inp=feed(*answers), lang="en",
                           open_page=(opened.append if opened is not None else None))
        return rc, buf.getvalue()

    def test_estimate_counts_frames_inside_sections(self):
        from kit import plan
        from kit.util import read_json
        from tests.test_m2 import do_plan
        ws = make_ws(self.tmp, self.base)
        with redirect_stdout(io.StringIO()):
            p, _ = do_plan(ws)
            from kit import pages
            pages.confirm(ws, p)
            runner.run(ws, log=lambda m: None)
        inv = read_json(os.path.join(ws.station, "inventory.json"))
        checked = 0
        for key, f in inv["files"].items():
            sc = read_json(os.path.join(ws.station, "screens", key + ".json"))
            if not sc:
                continue
            for pg in f["pages"]:
                real = sum(1 for s in sc["screens"] if s["pid"] == pg["id"])
                if real:
                    self.assertEqual(plan.page_estimate(pg["counts"]), real, pg["name"])
                    checked += 1
        self.assertGreaterEqual(checked, 3)
        self.assertEqual(plan.page_estimate({"FRAME": 2, "SECTION": 1}), 8)  # old inventories: the guess

    def test_later_runs_show_one_line_check(self):
        ws = make_ws(self.tmp, self.base)
        _, first = self.wizard(ws, "n")  # scan: no
        self.assertIn("– Figma desktop MCP (optional, off)", first)
        _, again = self.wizard(ws, "n")
        self.assertIn("Everything is still ready", again)
        self.assertNotIn("Figma desktop MCP", again)

    def test_plain_close_and_end_offers(self):
        ws = make_ws(self.tmp, self.base)
        self.wizard(ws, "", "", "n")  # scan, pages, don't start
        with redirect_stdout(io.StringIO()):
            runner.run(ws, log=lambda m: None)
        opened = []
        # close: yes · coverage page: yes · backup folder: yes
        rc, out = self.wizard(ws, "y", "y", "y", opened=opened)
        self.assertEqual(rc, 0, out)
        end = out[out.index("Step 6 of 6"):]
        for raw in ("# Close", "**", "](", "`"):
            self.assertNotIn(raw, end)
        self.assertIn("Problems: 0", end)
        self.assertIn("It links to the gallery of every file", end)
        self.assertEqual([os.path.basename(x) for x in opened], ["COVERAGE.html", "backup"])
        self.assertIn(ws.report_path, end)
        self.assertNotIn("python kit.py", out)

    def test_md_plain(self):
        from kit.util import md_plain
        self.assertEqual(md_plain("# Close\n\n- **changed: A** (run `python kit.py refresh`)\n- [C](x.html)"),
                         "Close\n\n- changed: A\n- C")


class Retest(unittest.TestCase):
    """Findings R1–R8 from the retest of the Windows ZIP."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_token_file_ends_with_the_line_it_talks_about(self):
        self.assertTrue(TOKEN_FILE_TEMPLATE.endswith("\nFIGMA_TOKEN=\n"))
        self.assertIn("right after FIGMA_TOKEN= on the last line", TOKEN_FILE_TEMPLATE)
        self.assertIn("after FIGMA_TOKEN= on its last line", i18n.t("token_drop"))
        self.assertIn("On its last line, paste the token right after FIGMA_TOKEN=", i18n.t("token_opened", editor="Notepad"))

    def test_token_file_accepts_where_people_paste(self):
        ws = Workspace(os.path.join(self.tmp, "ws"))
        ws.create()
        drop = os.path.join(self.tmp, "Figma token.txt")
        cases = {
            "after the equals sign": TOKEN_FILE_TEMPLATE.replace("FIGMA_TOKEN=\n", "FIGMA_TOKEN=figd_abc123\n"),
            "on the first line, where Notepad's cursor is": "figd_abc123" + TOKEN_FILE_TEMPLATE,
            "on a new line at the end": TOKEN_FILE_TEMPLATE + "figd_abc123\n",
        }
        for why, text in cases.items():
            with open(drop, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertTrue(take_token_file(ws, drop), why)
            self.assertEqual(figapi.read_token(ws)[0], "figd_abc123", why)
            with open(drop, encoding="utf-8") as f:
                self.assertEqual(f.read(), TOKEN_FILE_TEMPLATE, why)
        self.assertFalse(take_token_file(ws, drop))  # the empty template holds no token

    def test_token_file_in_the_windows_zip(self):
        (z,) = [p for p in build_downloads.build(self.tmp) if p.endswith("windows.zip")]
        with zipfile.ZipFile(z) as f:
            data = f.read("Figma token.txt")
        self.assertTrue(data.endswith(b"\r\nFIGMA_TOKEN=\r\n"))

    def test_persian_digits_and_both_kinds_typed(self):
        self.assertEqual(i18n.t("step", "fa", n=1, total=6, title="x"), "قدم ۱ از ۶ · x")
        self.assertEqual(i18n.normalize("۲"), "2")
        self.assertIn("حدود ۲۴ مگابایت", i18n.plan_summary(
            {"files": 1, "projects": 1, "pages": 1, "screens_est": 3, "minutes_est": 1, "mb_est": 24, "gb_est": 0}, "fa"))

    def test_persian_checklist(self):
        from kit import doctor
        c = {"python": {"status": "ok", "detail": "Python 3.14.7", "required": True, "fix": []},
             "token": {"status": "missing", "detail": "no Figma token found", "required": True, "fix": ["Make one."]},
             "desktop_mcp": {"status": "missing", "detail": "x", "required": False, "fix": ["y"]}}
        out = doctor.render_plain({"checks": c}, "fa")
        self.assertIn("✔ پایتون", out)
        self.assertIn("– MCP فیگمای دسکتاپ (اختیاری، خاموش)", out)
        self.assertIn("توکن فیگما", out)
        self.assertNotIn("Python 3.14.7", out)

    def test_outage_wording(self):
        saved = (figapi.reachable, figapi.nap)
        answers = iter([(False, "timed out"), (True, "")])
        figapi.reachable, figapi.nap = (lambda *a, **k: next(answers)), (lambda *a, **k: None)
        lines = []
        try:
            runner.wait_for_figma(lines.append)
        finally:
            figapi.reachable, figapi.nap = saved
        self.assertIn("Can't reach Figma: check your internet or VPN. Trying again in 60s", lines[0])
        self.assertNotIn("not reachable", lines[0])


class PersianPages(unittest.TestCase):
    def test_pages_in_persian_without_markdown_in_start(self):
        srv, base = fake_figma.start()
        saved = (figapi.API, figapi.MIN_GAP)
        figapi.API, figapi.MIN_GAP = base, 0
        tmp = tempfile.mkdtemp()
        try:
            from kit import pages
            from kit.util import md_plain
            from tests.test_m2 import do_plan
            ws = make_ws(tmp, base, language="fa")
            with redirect_stdout(io.StringIO()):
                do_plan(ws)
            text = pages.render(ws)
            self.assertIn("# صفحه‌ها", text)
            self.assertIn("(جداکننده)", text)
            self.assertIn("حدود ۵ فریم", text)
            self.assertNotIn("screens", text)
            plain = md_plain(pages.render(ws, "fa"))
            self.assertNotIn("#", plain)
            self.assertIn("  ۳. ✔ Screens", plain)
            self.assertIn("backed up", pages.render(ws, "en"))
        finally:
            figapi.API, figapi.MIN_GAP = saved
            srv.shutdown()
            srv.server_close()
            shutil.rmtree(tmp, ignore_errors=True)


class Cli(unittest.TestCase):
    def test_plan_summary_in_cli(self):
        t = {"files": 1, "projects": 1, "pages": 2, "screens_est": 1, "minutes_est": 1, "mb_est": 3, "gb_est": 0.0}
        self.assertEqual(cli.plan_summary({"totals": t}), "1 file in 1 project · 2 pages · ≈ 1 screen · ≈ 1 min · ≈ 3 MB")


if __name__ == "__main__":
    unittest.main()
