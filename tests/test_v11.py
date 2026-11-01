"""1.1 tests: the guided start (kit.py start) and doctor --redact."""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from kit import doctor, figapi, pages, runner, start
from kit.util import read_json
from kit.workspace import Workspace
from tests import fake_figma
from tests.test_m2 import make_ws


def feed(*answers):
    it = iter(answers)
    return lambda prompt="": next(it)


class GuidedStart(unittest.TestCase):
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

    def wizard(self, ws, *answers, opened=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = start.run(ws.root, inp=feed(*answers), open_page=(opened.append if opened is not None else None))
        return rc, buf.getvalue()

    def test_walks_from_setup_to_closed(self):
        ws = make_ws(self.tmp, self.base)
        # scan: yes · pages as suggested: yes · start the backup now: no
        rc, out = self.wizard(ws, "", "", "n")
        self.assertEqual(rc, 0, out)
        p = read_json(os.path.join(ws.station, "plan.json"))
        self.assertTrue(pages.confirmed(ws, p))
        self.assertIn("Step 5 of 6", out)

        with redirect_stdout(io.StringIO()):
            self.assertEqual(runner.run(ws), 0)  # the export itself, in this process
        opened = []
        # close now: yes · open the coverage page: yes · open the backup folder: no
        rc, out = self.wizard(ws, "y", "y", "n", opened=opened)
        self.assertEqual(rc, 0, out)
        self.assertEqual(ws.state()["phase"], "closed")
        self.assertEqual([os.path.basename(x) for x in opened], ["COVERAGE.html"])

    def test_choose_pages_file_by_file(self):
        ws = make_ws(self.tmp, self.base)
        # scan: yes · suggested pages: no → file 1: only page 1 · file 2: keep · start: no
        rc, out = self.wizard(ws, "y", "n", "1", "", "n")
        self.assertEqual(rc, 0, out)
        p = read_json(os.path.join(ws.station, "plan.json"))
        self.assertTrue(pages.confirmed(ws, p))
        first = pages.files(ws)[0][3]
        self.assertEqual([pg["export"] for _, pg in first][0], True)
        self.assertFalse(any(pg["export"] for _, pg in first[1:]))

    def test_waits_for_token(self):
        ws = make_ws(self.tmp, self.base)
        with open(ws.env_path, "w", encoding="utf-8") as f:
            f.write("FIGMA_TOKEN=\n")
        rc, out = self.wizard(ws, "3")  # token: later
        self.assertEqual(rc, 0)
        self.assertIn(ws.env_path, out)
        self.assertNotIn("Step 3", out)


class Redact(unittest.TestCase):
    def test_hides_folders_and_handle(self):
        ws = Workspace(os.path.join(os.path.expanduser("~"), "Figma Backup"))
        home_file = os.path.join(os.path.expanduser("~"), "AppData", "Figma.exe")
        text = (f"signed in as Jane Doe), from env | {ws.root} | {home_file} | "
                + json.dumps({"p": ws.root, "q": home_file}))
        out = doctor.redact(text, ws)
        for secret in ("Jane Doe", ws.root, os.path.expanduser("~"), json.dumps(ws.root)[1:-1]):
            self.assertNotIn(secret, out)
        self.assertIn("signed in as <you>", out)
        self.assertIn("<workspace>", out)


if __name__ == "__main__":
    unittest.main()
