"""1.2 tests, third part: retest findings R9 (stalled downloads, fast pause, stall line) and R10 (a new copy of the
kit pointed at an existing backup folder continues it)."""
import http.server
import io
import os
import shutil
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout

from kit import export, figapi, runner, start, workspace
from tests import fake_figma
from tests.test_m2 import make_ws
from tests.test_v12 import feed


class Trickle(http.server.BaseHTTPRequestHandler):
    """An image server whose connection stalls: a byte now and then, never enough to trip the idle timeout."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "100000")
        self.end_headers()
        try:
            for _ in range(200):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.05)
        except OSError:
            pass

    def log_message(self, *a):
        pass


class Stalls(unittest.TestCase):
    def setUp(self):
        self.saved = (figapi.BASE_DEADLINE, figapi.MIN_SPEED, figapi.nap, figapi.STOP_HOOK)
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        figapi.BASE_DEADLINE, figapi.MIN_SPEED, figapi.nap, figapi.STOP_HOOK = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Trickle)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_address[1]}/img.png"

    def test_stalled_download_fails_and_is_retried(self):
        url = self.serve()
        figapi.BASE_DEADLINE, figapi.MIN_SPEED = 0.5, 10**9
        naps = []
        figapi.nap = lambda s, kind=None: naps.append(s)
        t0 = time.time()
        with self.assertRaises(TimeoutError):
            export._fetch(url, os.path.join(self.tmp, "a.png"), tries=2)
        self.assertLess(time.time() - t0, 6)
        self.assertEqual(len(naps), 2)  # each stall counted as a failure, then tried again
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "a.png")))

    def test_pause_ends_a_download_within_seconds(self):
        url = self.serve()
        asked = []
        figapi.STOP_HOOK = lambda: bool(asked)
        threading.Timer(0.3, lambda: asked.append(1)).start()
        t0 = time.time()
        with self.assertRaises(export.Stopped):
            export._fetch(url, os.path.join(self.tmp, "b.png"))
        self.assertLess(time.time() - t0, 3)

    def test_pause_ends_a_wait(self):
        figapi.STOP_HOOK = lambda: True
        t0 = time.time()
        with self.assertRaises(figapi.Stopped):
            self.saved[2](30, "network")  # the real nap
        self.assertLess(time.time() - t0, 2)


class Views(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL, start.STALL)
        figapi.API, figapi.MIN_GAP = cls.base, 0
        start.RTL_TERMINAL = False

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL, start.STALL = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_live_view_says_when_nothing_moves(self):
        ws = make_ws(self.tmp, self.base)
        with redirect_stdout(io.StringIO()):
            start.run(ws.root, inp=feed("", "", "n"), lang="en")  # scan, pages, don't start
        ticks = iter(range(4))
        saved = (runner.running, start.status_line)
        runner.running = lambda w: next(ticks, None) is not None
        start.status_line = lambda *a, **k: ("Onboarding · PNG 1/5 · SVG 0/5", ("same",), "≈ 6 min left")
        start.STALL = 0
        w = start.Wizard(ws.root, feed(), "en", None, None, None)
        w.poll = lambda s: None
        from kit.util import read_json
        p = read_json(os.path.join(ws.station, "plan.json"))
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                start.watch(w, ws, p)
        finally:
            runner.running, start.status_line = saved
        self.assertIn("No new screen for", buf.getvalue())

    def test_new_copy_continues_an_existing_backup(self):
        ws = make_ws(os.path.join(self.tmp, "my-backup"), self.base)
        with redirect_stdout(io.StringIO()):
            start.run(ws.root, inp=feed("n"), lang="en")  # an earlier session: scan no
        if os.path.exists(workspace.POINTER):
            os.remove(workspace.POINTER)  # a new copy of the kit: no pointer
        buf = io.StringIO()
        with redirect_stdout(buf):
            # language: English · folder: the existing one · continue it: yes · scan now: no
            rc = start.run(None, inp=feed("2", ws.root, "", "n"))
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("Found an existing backup in this folder", out)
        self.assertNotIn("What should be backed up?", out)
        self.assertIn("Scan Figma now", out)
        with open(workspace.POINTER, encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), ws.root)
        with open(ws.report_path, encoding="utf-8") as f:
            self.assertIn("Opened again with a new copy of the kit", f.read())

    def test_saying_no_asks_the_questions(self):
        ws = make_ws(os.path.join(self.tmp, "my-backup"), self.base)
        if os.path.exists(workspace.POINTER):
            os.remove(workspace.POINTER)
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                start.run(None, inp=feed("2", ws.root, "n"))  # continue it: no → the next question
            except StopIteration:
                pass
        self.assertIn("What should be backed up?", buf.getvalue())

    def test_time_left_holds_while_nothing_moves(self):
        from kit.util import read_json, write_json
        from tests.test_m2 import do_plan
        ws = make_ws(self.tmp, self.base)
        with redirect_stdout(io.StringIO()):
            p, _ = do_plan(ws)
            sc = export.list_screens(ws, p["queue"][0] if p["queue"][0]["pages"] else p["queue"][1], fake_figma.TOKEN,
                                     log=lambda m: None)
        st = ws.state()
        st["files"] = {sc["key"]: {"status": "running"}}
        write_json(ws.state_path, st)
        w = start.Wizard(ws.root, feed(), "en", None, None, None)
        p = read_json(os.path.join(ws.station, "plan.json"))
        line, sig, left = start.status_line(w, ws, p, time.time() - 600, 0)
        self.assertIn("min left", left)
        held, sig2, _ = start.status_line(w, ws, p, time.time() - 1200, 0, hold=left)
        self.assertEqual(sig, sig2)
        self.assertIn(f"{left} · waiting…", held)  # the same estimate, not one that grows

    def test_persian_report_is_persian_and_rtl(self):
        import re
        from kit import runner
        ws = make_ws(self.tmp, self.base, language="fa")
        with redirect_stdout(io.StringIO()):
            start.run(ws.root, inp=feed("", "", "n"), lang="fa")  # scan · pages · don't start yet
            runner.run(ws, log=lambda m: None)
            start.run(ws.root, inp=feed("y", "n", "n"), lang="fa")  # check and pack · coverage: no · folder: no
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("# گزارش پشتیبان فیگما\n"))
        self.assertIn('<div dir="rtl">', text)
        self.assertTrue(text.rstrip().endswith("</div>"))
        for heading in ("## گزارش کارها", "## تنظیمات: تصمیم‌های شما", "## بررسی", "## برنامه", "## صفحه‌ها", "## اجرا", "## پایان"):
            self.assertIn(heading, text)
        for english in ("I can do", "Optional", "## Plan", "## Run", "## Close", " screens", "Problems", "file in"):
            self.assertNotIn(english, text)
        self.assertLess(text.index("## گزارش کارها"), text.index("## تنظیمات"))  # the log first
        log = text[text.index("## گزارش کارها"):text.index("<!-- /kit:log -->")]
        entries = [ln for ln in log.splitlines() if ln.startswith("- ")]
        self.assertIn("وارسی و آرشیو", entries[0])  # newest first
        for ln in entries:
            self.assertFalse(re.search(r"[0-9]", ln.split(" · ", 1)[1].split(" (")[0].replace("Onboarding", "")), ln)


if __name__ == "__main__":
    unittest.main()
