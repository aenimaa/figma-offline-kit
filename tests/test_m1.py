"""M1 tests: interview validation, team links, token handling, report sections. Run: python -m unittest"""
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
import io
from unittest import mock

from kit import doctor, figapi, interview, report
from kit.workspace import Workspace

TEAM = "https://www.figma.com/files/team/1234567890/Example-Team"
FAKE_TOKEN = "figd_FAKE-test-token-0000"


class TeamLink(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(figapi.team_id(TEAM), "1234567890")
        self.assertEqual(figapi.team_id("https://www.figma.com/files/1111/team/2222/X?fuid=3"), "2222")
        self.assertEqual(figapi.team_id("2222"), "2222")
        self.assertIsNone(figapi.team_id("https://www.figma.com/design/abc/File"))
        self.assertIsNone(figapi.team_id(""))


class Validate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_defaults_are_valid(self):
        cfg, errors, _ = interview.validate({"workspace": self.tmp, "team": TEAM})
        self.assertEqual(errors, [])
        self.assertEqual(cfg["mode"], "project")
        self.assertEqual(cfg["archive_format"], "zip")
        self.assertTrue(cfg["addons"]["coverage"])
        self.assertFalse(cfg["addons"]["handoff"])

    def test_errors(self):
        _, errors, _ = interview.validate({"workspace": self.tmp, "team": "nope", "mode": "fast",
                                           "pages": "named", "formats": []})
        text = " ".join(errors)
        for key in ("team:", "mode:", "page_names:", "formats:"):
            self.assertIn(key, text)

    def test_team_or_files(self):
        cfg, errors, _ = interview.validate({"workspace": self.tmp, "team": "https://www.figma.com/design/AbCdEfGhIj12/X?node-id=1-2"})
        self.assertEqual(errors, [])
        self.assertEqual((cfg["team"]["id"], cfg["files"]), (None, ["AbCdEfGhIj12"]))
        _, errors, _ = interview.validate({"workspace": self.tmp, "team": TEAM + ", https://www.figma.com/design/AbCdEfGhIj12/X"})
        self.assertTrue(any("not both" in e for e in errors))

    def test_workspace_not_the_kit(self):
        from kit.util import REPO
        _, errors, _ = interview.validate({"workspace": REPO, "team": TEAM})
        self.assertTrue(any(e.startswith("workspace:") for e in errors))
        _, errors, _ = interview.validate({"workspace": os.path.dirname(REPO), "team": TEAM})
        self.assertTrue(any(e.startswith("workspace:") for e in errors))

    def test_comma_lists_and_conditions(self):
        cfg, errors, _ = interview.validate({"workspace": self.tmp, "team": TEAM, "pages": "named",
                                             "page_names": "Ready, Shipped ", "addons": "coverage"})
        self.assertEqual(errors, [])
        self.assertEqual(cfg["pages"]["names"], ["Ready", "Shipped"])
        self.assertEqual(cfg["pages"]["archive_words"], [])
        self.assertEqual(cfg["archive_format"], "none")  # archives not chosen

    def test_warning_without_desktop_control(self):
        _, _, warnings = interview.validate({"workspace": self.tmp, "team": TEAM, "local_copies": "auto"},
                                            {"ai": {"desktop-control": "no"}})
        self.assertTrue(any("guided" in w for w in warnings))

    def test_terminal_interview_accepts_numbers(self):
        replies = iter([self.tmp, TEAM, "1", "", "", "1,2", "1,4", "2", "", ""])
        with redirect_stdout(io.StringIO()):
            answers = interview.ask_terminal(inp=lambda _: next(replies))
        cfg, errors, _ = interview.validate(answers)
        self.assertEqual(errors, [])
        self.assertEqual(cfg["mode"], "full")
        self.assertEqual(cfg["local_copies"], "guided")
        self.assertTrue(cfg["addons"]["tokens"])


class TokenAndDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ws = Workspace(self.tmp)
        self.ws.create()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_env_template_has_no_token(self):
        with mock.patch.dict(os.environ, {"FIGMA_TOKEN": ""}):
            self.assertEqual(figapi.read_token(self.ws), (None, None))

    def test_token_from_env_file(self):
        with open(self.ws.env_path, "w", encoding="utf-8") as f:
            f.write(f'FIGMA_TOKEN="{FAKE_TOKEN}"\n')
        with mock.patch.dict(os.environ, {"FIGMA_TOKEN": ""}):
            self.assertEqual(figapi.read_token(self.ws), (FAKE_TOKEN, "workstation/.env"))

    def test_doctor_never_prints_the_token(self):
        with open(self.ws.env_path, "w", encoding="utf-8") as f:
            f.write(f"FIGMA_TOKEN={FAKE_TOKEN}\n")
        me = {"handle": "tester"}
        with mock.patch.dict(os.environ, {"FIGMA_TOKEN": ""}), \
                mock.patch.object(figapi, "reachable", return_value=(True, "")), \
                mock.patch.object(figapi, "get", return_value=me), \
                mock.patch("kit.mcp.probe", return_value=(False, "refused")):
            r = doctor.run(self.ws, ai={"desktop-control": "yes"})
        dump = json.dumps(r) + doctor.render(r) + open(self.ws.doctor_path, encoding="utf-8").read()
        self.assertNotIn(FAKE_TOKEN, dump)
        self.assertEqual(r["checks"]["token"]["status"], "ok")

    def test_parse_ai(self):
        self.assertEqual(doctor.parse_ai("desktop-control=yes, figma-mcp=No"),
                         {"desktop-control": "yes", "figma-mcp": "no"})


class Report(unittest.TestCase):
    def test_sections_replace_in_place_and_keep_order(self):
        tmp = tempfile.mkdtemp()
        try:
            ws = Workspace(tmp)
            ws.create()
            report.update(ws, "config", "# Settings\n\none")
            report.update(ws, "doctor", "# Doctor\n\n## I can do\n\nx")
            report.update(ws, "config", "# Settings\n\ntwo")
            text = open(ws.report_path, encoding="utf-8").read()
            self.assertNotIn("one", text)
            self.assertLess(text.index("## Settings"), text.index("## Doctor"))  # decisions first
            self.assertIn("### I can do", text)
            self.assertNotIn("#### I can do", text)  # stored sections are not shifted twice
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
