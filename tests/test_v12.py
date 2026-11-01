"""1.2 tests: language in the guided start, the token step, and the two downloads (layout, CRLF, mode bits)."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout

from kit import figapi, start
from kit.figapi import read_token
from kit.workspace import Workspace, clean_token
from tests import fake_figma
from tests.test_m2 import make_ws


def feed(*answers):
    """Like input(): shows the prompt, then gives the next answer."""
    it = iter(answers)

    def inp(prompt=""):
        print(prompt)
        return next(it)
    return inp
from tools import build_downloads

TEAM = f"https://www.figma.com/files/team/{fake_figma.TEAM_ID}/Example-Team"


class Wizard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = fake_figma.start()
        cls.saved = (figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL)
        figapi.API, figapi.MIN_GAP = cls.base, 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        figapi.API, figapi.MIN_GAP, start.RTL_TERMINAL = cls.saved

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ.pop("FIGMA_TOKEN", None)
        start.RTL_TERMINAL = False

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wizard(self, ws_root, *answers, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = start.run(ws_root, inp=feed(*answers), **kw)
        return rc, buf.getvalue()

    def test_language_first_then_persian_interview(self):
        root = os.path.join(self.tmp, "ws")
        pasted = []
        # (a terminal that shows Persian, e.g. macOS) language: 1 = فارسی · interview: folder, team, then
        # defaults, local copies: ۲ = not now · token: paste (default) · scan now: no
        rc, out = self.wizard(root, "۱", root, TEAM, "", "", "", "", "", "۲", "", "", "n",
                              secret=lambda prompt: pasted.append(prompt) or fake_figma.TOKEN)
        self.assertEqual(rc, 0, out)
        ws = Workspace(root)
        self.assertEqual(ws.config()["language"], "fa")
        self.assertEqual(ws.config()["local_copies"], "skip")
        self.assertIn("قدم ۱ از ۶", out)  # Persian digits in Persian text
        self.assertIn("  ۱. ", out)
        self.assertNotIn("قدم 1", out)
        self.assertIn("پشتیبان در کدام پوشه ذخیره شود؟", out)
        self.assertNotIn("زبان گزارش‌ها", out)  # the language is asked once, at the start
        self.assertEqual(out.count("Language / زبان"), 1)
        self.assertIn("Ctrl+V", pasted[0])
        self.assertIn(ws.env_path, out)
        self.assertNotIn(fake_figma.TOKEN, out)
        self.assertEqual(read_token(ws)[0], fake_figma.TOKEN)

    def test_lang_flag_skips_the_question_and_is_remembered(self):
        ws = make_ws(self.tmp, self.base)
        rc, out = self.wizard(ws.root, "n", lang="fa")  # scan now: no
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Language / زبان", out)
        self.assertEqual(ws.config()["language"], "fa")
        rc, out = self.wizard(ws.root, "n")  # next time: no question, Persian again
        self.assertNotIn("Language / زبان", out)
        self.assertIn("الان فیگما خوانده شود؟", out)

    def test_windows_window_stays_english_report_in_persian(self):
        ws = make_ws(self.tmp, self.base)
        start.RTL_TERMINAL = True  # Windows terminals: no right-to-left layout
        menu = io.StringIO()
        with redirect_stdout(menu):
            self.assertEqual(start.ask_language(feed("۱")), "fa")
        self.assertIn("Persian (Farsi)", menu.getvalue())
        self.assertFalse(any("؀" <= ch <= "ۿ" for ch in menu.getvalue()), menu.getvalue())
        rc, out = self.wizard(ws.root, "n", lang="fa")  # scan now: no
        self.assertEqual(rc, 0, out)
        self.assertIn("Scan Figma now", out)
        self.assertFalse(any("؀" <= ch <= "ۿ" for ch in out), out)  # this window stays English
        self.assertEqual(ws.config()["language"], "fa")
        with open(ws.report_path, encoding="utf-8") as f:
            self.assertIn("تنظیمات: تصمیم‌های شما", f.read())

    def test_token_paste_is_cleaned_checked_and_never_shown(self):
        ws = make_ws(self.tmp, self.base)
        with open(ws.env_path, "w", encoding="utf-8") as f:
            f.write("FIGMA_TOKEN=\n")
        tokens = iter(["figd_WRONG-token", f"  FIGMA_TOKEN={fake_figma.TOKEN} \n"])
        # menu: paste (wrong token, refused) · paste again · scan now: no
        rc, out = self.wizard(ws.root, "1", "1", "n", lang="en", secret=lambda prompt: next(tokens))
        self.assertEqual(rc, 0, out)
        self.assertIn("Figma refused this token (403)", out)
        self.assertIn("The token works (signed in as tester)", out)
        self.assertNotIn("figd_WRONG", out)
        self.assertNotIn(fake_figma.TOKEN, out)
        with open(ws.env_path, encoding="utf-8") as f:
            env = f.read()
        self.assertTrue(env.startswith("# Figma personal access token"))
        self.assertIn(f"\nFIGMA_TOKEN={fake_figma.TOKEN}\n", env)

    def test_token_open_file_then_recheck(self):
        ws = make_ws(self.tmp, self.base)
        with open(ws.env_path, "w", encoding="utf-8") as f:
            f.write("FIGMA_TOKEN=\n")
        opened = []

        def editor(path):  # the person pastes the token in Notepad / TextEdit and saves
            opened.append(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"FIGMA_TOKEN={fake_figma.TOKEN}\n")

        rc, out = self.wizard(ws.root, "2", "", "n", lang="en", open_file=editor)
        self.assertEqual(rc, 0, out)
        self.assertEqual(opened, [ws.env_path])
        self.assertIn("The token works", out)

    def test_clean_token(self):
        for raw in ("abc", " abc\n", "FIGMA_TOKEN=abc", '"abc"', "a b c", "figma_token='abc'"):
            self.assertEqual(clean_token(raw), "abc", raw)


class Downloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.zips = dict(zip(("windows", "macos"), build_downloads.build(cls.tmp)))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_layout(self):
        for os_name, start_file in (("windows", "Start.bat"), ("macos", "Start.command")):
            with zipfile.ZipFile(self.zips[os_name]) as z:
                names = z.namelist()
            self.assertEqual(os.path.basename(self.zips[os_name]), f"figma-offline-kit-{os_name}.zip")
            self.assertEqual(sorted({n.split("/")[0] + ("/" if "/" in n else "") for n in names}),
                             sorted([start_file, "Read me first.html", "Figma token.txt", "app/", "guides/"]))
            for must in ("app/kit.py", "app/kit/start.py", "app/kit/i18n.py", "app/templates/gallery.html",
                         "app/templates/variables.js", "app/LICENSE", "app/CHANGELOG.md", "guides/figma-token.md"):
                self.assertIn(must, names)
            for never in ("AGENTS.md", "CLAUDE.md", "tests/", "__pycache__", ".env", "BRIEF.md", "examples/"):
                self.assertFalse(any(never in n for n in names), never)

    def test_line_endings_and_modes(self):
        with zipfile.ZipFile(self.zips["windows"]) as z:
            bat = z.read("Start.bat")
            self.assertGreater(bat.count(b"\r\n"), 10)
            self.assertEqual(bat.count(b"\n"), bat.count(b"\r\n"))
            self.assertNotIn(b"\r\n", z.read("app/kit/start.py"))
        with zipfile.ZipFile(self.zips["macos"]) as z:
            info = z.getinfo("Start.command")
            self.assertEqual(info.create_system, 3)
            self.assertEqual((info.external_attr >> 16) & 0o777, 0o755)
            self.assertNotIn(b"\r", z.read("Start.command"))
            self.assertTrue(z.read("Start.command").startswith(b"#!/bin/bash\n"))
            self.assertEqual((z.getinfo("app/kit.py").external_attr >> 16) & 0o777, 0o644)

    def test_read_me_first(self):
        for os_name, env in (("windows", r"C:\Users\&lt;you&gt;\figma-backup\workstation\.env"),
                             ("macos", "/Users/&lt;you&gt;/figma-backup/workstation/.env")):
            with zipfile.ZipFile(self.zips[os_name]) as z:
                page = z.read("Read me first.html").decode("utf-8")
            self.assertIn(env, page)
            self.assertIn("Python 3.10", page)
            self.assertIn("پایتون ۳٫۱۰", page)
            self.assertIn('dir="rtl"', page)

    def test_reproducible_and_current(self):
        again = build_downloads.build(os.path.join(self.tmp, "again"))
        for a, b in zip(self.zips.values(), again):
            with open(a, "rb") as f1, open(b, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(build_downloads.main(["--check"]), 0,
                             "downloads/ is out of date: run python tools/build_downloads.py")

    def test_unzipped_kit_runs(self):
        dest = os.path.join(self.tmp, "unzipped")
        with zipfile.ZipFile(self.zips["windows"]) as z:
            z.extractall(dest)
        code = ("import os; from kit import gallery, variables, util, VERSION; "
                "assert os.path.exists(gallery.TEMPLATE) and os.path.exists(variables.SCRIPT); "
                "assert util.guide('figma-token.md').endswith(os.path.join('guides', 'figma-token.md')); print(VERSION)")
        r = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(dest, "app"), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        env = dict(os.environ, FIGMA_KIT_WORKSPACE=os.path.join(self.tmp, "ws-launch"), PYTHONIOENCODING="utf-8")
        env.pop("FOK_PAUSE", None)
        if os.name == "nt":
            cmd = ["cmd", "/c", os.path.join(dest, "Start.bat"), "--lang", "en"]
        elif shutil.which("bash"):
            with zipfile.ZipFile(self.zips["macos"]) as z:
                z.extractall(dest)
            cmd = ["bash", os.path.join(dest, "Start.command"), "--lang", "en"]
        else:
            self.skipTest("no shell to run the start file")
        r = subprocess.run(cmd, input="\n", capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        self.assertIn("guided start", r.stdout, r.stdout + r.stderr)
        self.assertIn("Step 1 of 6", r.stdout)
        self.assertTrue(os.path.exists(os.path.join(dest, "app", ".workspace")) is False)


if __name__ == "__main__":
    unittest.main()
