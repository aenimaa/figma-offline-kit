"""M3 tests: local copies checklist, close (verify · drift · coverage · archives) and refresh, against the fake server."""
import os
import shutil
import tempfile
import time
import unittest
import zipfile

from kit import close, copies, figapi, runner
from kit.doctor import find_tool
from kit.util import read_json, write_json
from tests import fake_figma
from tests.test_m2 import QUIET, do_plan, make_ws, read


class Base(unittest.TestCase):
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


class Copies(Base):
    def setUp(self):
        super().setUp()
        self.ws = make_ws(self.tmp, self.base, local_copies="guided")
        do_plan(self.ws)
        self.opened = []

    def open(self, ref, force=False):
        return copies.open_file(self.ws, ref, force=force, launch_fn=self.opened.append)

    def test_checklist_and_pacing(self):
        data = copies.sync(self.ws)
        rows = copies.ordered(data)
        self.assertEqual([(r["name"], os.path.splitext(r["target"])[1]) for r in rows],
                         [("Flows", ".jam"), ("Onboarding", ".fig"), ("Landing", ".fig")])
        self.assertEqual(rows[0]["url"], "figma://file/FAKEkeyBBB2")
        rec = self.open("Onboarding")
        self.assertEqual(self.opened, ["figma://file/FAKEkeyAAA1"])
        self.assertEqual(rec["status"], "opened")
        with self.assertRaisesRegex(ValueError, "wait"):
            self.open("3")
        self.open("3", force=True)
        data = read_json(copies.path(self.ws))
        for r in data["items"].values():
            r["opened"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        data["items"].update({f"x{i}": {"opened": time.strftime("%Y-%m-%dT%H:%M:%S")} for i in range(40)})
        self.assertEqual(copies.wait_seconds(data), -1)

    def test_guided_save_is_filed_and_checked(self):
        self.open("Onboarding")
        inbox = copies.inboxes(self.ws)[0]
        os.makedirs(inbox)
        with open(os.path.join(inbox, "Onboarding (1).fig"), "wb") as f:
            f.write(b"fig-kiwi" + b"\0" * 100)
        found = copies.check(self.ws, log=QUIET)
        self.assertEqual([r["name"] for r in found], ["Onboarding"])
        tgt = os.path.join(self.ws.backup, "Mobile App", "Onboarding", "Onboarding.fig")
        self.assertTrue(os.path.exists(tgt))
        self.assertEqual(os.listdir(inbox), [])
        self.assertIn("**1 / 3** saved", copies.render(self.ws))

    def test_damaged_copy_fails(self):
        r = copies.sync(self.ws)["items"]["FAKEkeyCCC3"]
        os.makedirs(os.path.dirname(r["target"]), exist_ok=True)
        with open(r["target"], "wb") as f:
            f.write(b"<html>not a figma file")
        copies.check(self.ws, log=QUIET)
        self.assertEqual(read_json(copies.path(self.ws))["items"]["FAKEkeyCCC3"]["status"], "failed")

    def test_skip(self):
        copies.skip(self.ws, "Flows", "view only")
        self.assertIn("⏭ (view only)", copies.render(self.ws))


class Close(Base):
    def test_close_refresh_cycle(self):
        ws = make_ws(self.tmp, self.base)
        do_plan(ws)
        runner.run(ws, log=QUIET)
        v = close.verify(ws)
        self.assertEqual(v["problems"], [])
        self.assertEqual((v["totals"]["screens"], v["totals"]["pdf"], v["totals"]["empty"]), (9, 1, 1))

        d = close.drift(ws, fake_figma.TOKEN, log=QUIET)
        self.assertFalse(any(x["edited_after"] for x in d["files"].values()))
        cov = read(close.coverage(ws))
        for s in ("Onboarding", "Archive v1", "not backed up (archive)", "current as of"):
            self.assertIn(s, cov)
        arch = close.archives(ws, log=QUIET)
        self.assertEqual(len(arch), 2)
        with zipfile.ZipFile(os.path.join(ws.backup, "Website.zip")) as z:
            self.assertIn("Website/Landing/index.html", z.namelist())
            self.assertIsNone(z.testzip())
        self.assertTrue(all(note == "up to date" for _, note in close.archives(ws, log=QUIET)))

        old = fake_figma.FILES["FAKEkeyCCC3"]["lastModified"]
        fake_figma.FILES["FAKEkeyCCC3"]["lastModified"] = "2026-12-01T00:00:00Z"
        try:
            d = close.drift(ws, fake_figma.TOKEN, log=QUIET)
            self.assertTrue(d["files"]["FAKEkeyCCC3"]["edited_after"])
            self.assertIn("edited in Figma", read(close.coverage(ws)))
            self.assertEqual(close.refresh(ws), ["Landing"])
            self.assertFalse(os.path.exists(os.path.join(ws.backup, "Website", "Landing")))
            replaced = os.path.join(ws.temp, "replaced")
            self.assertTrue(any("index.html" in fs for _, _, fs in os.walk(replaced)))
            runner.run(ws, log=QUIET)  # no new plan needed
            self.assertEqual(ws.state()["files"]["FAKEkeyCCC3"]["last_modified"], "2026-12-01T00:00:00Z")
            self.assertFalse(close.drift(ws, fake_figma.TOKEN, log=QUIET)["files"]["FAKEkeyCCC3"]["edited_after"])
        finally:
            fake_figma.FILES["FAKEkeyCCC3"]["lastModified"] = old

    def test_7z_archive(self):
        if not find_tool(["7z", "7zz", "7za"], [os.path.join("7-Zip", "7z.exe")]):
            self.skipTest("7-Zip not installed")
        src = os.path.join(self.tmp, "Proj")
        os.makedirs(os.path.join(src, "File"))
        write_json(os.path.join(src, "File", "a.json"), {"x": 1})
        out = os.path.join(self.tmp, "Proj.7z")
        close.archive_one(src, out, "7z")
        self.assertGreater(os.path.getsize(out), 0)


if __name__ == "__main__":
    unittest.main()


class Tokens(Base):
    def setUp(self):
        super().setUp()
        self.ws = make_ws(self.tmp, self.base, addons=["tokens"])
        do_plan(self.ws)
        runner.run(self.ws, log=QUIET)
        self.q = {x["key"]: x for x in read_json(os.path.join(self.ws.station, "plan.json"))["queue"]}

    def test_rest_variables_and_css(self):
        from kit import variables
        self.assertIsNotNone(variables.from_rest(self.ws, self.q["FAKEkeyAAA1"], fake_figma.TOKEN, log=QUIET))
        self.assertIsNone(variables.from_rest(self.ws, self.q["FAKEkeyCCC3"], fake_figma.TOKEN, log=QUIET))
        css = read(os.path.join(variables.var_dir(self.ws, self.q["FAKEkeyAAA1"]), "tokens.css"))
        self.assertIn("--brand: #5a78dc;", css)          # Web code syntax wins
        self.assertIn("--color-bg: #eeeeff;", css)       # else the slugged path
        self.assertIn("--space-m: 16px;", css)
        self.assertIn('[data-colors="dark"] {', css)
        self.assertIn("--color-bg: var(--brand);", css)  # alias in the dark mode
        scss = read(os.path.join(variables.var_dir(self.ws, self.q["FAKEkeyAAA1"]), "_tokens.scss"))
        self.assertIn("$brand: var(--brand);", scss)

    def test_token_svgs_hybrid(self):
        from kit import gallery, tokens, variables
        from kit.export import screens_path
        variables.from_rest(self.ws, self.q["FAKEkeyAAA1"], fake_figma.TOKEN, log=QUIET)
        VARS = variables.load_all(self.ws, self.q.values())
        res = tokens.run_file(self.ws, self.q["FAKEkeyAAA1"], VARS, fake_figma.TOKEN, log=QUIET)
        self.assertEqual(res["by_method"], {"hex": 1, "render": 1})
        sc = read_json(screens_path(self.ws, "FAKEkeyAAA1"))
        U = read_json(tokens.usage_path(self.ws, sc))["screens"]
        by = {s["name"]: (s, U[s["id"]]) for s in sc["screens"]}
        self.assertEqual(by["Welcome"][1]["method"], "hex")
        self.assertEqual(by["Email"][1]["method"], "render")
        self.assertEqual(by["Home"][1]["svg"], "raw")
        self.assertEqual(by["Home"][1]["unbound_colors"][0]["hex"], "#FF0000")
        welcome = read(tokens.tok_path(self.ws, sc, by["Welcome"][0]))
        self.assertIn("fill:var(--brand, #5A78DC)", welcome)
        self.assertIn("fill:var(--color-bg, #EEEEFF)", welcome)
        email = read(tokens.tok_path(self.ws, sc, by["Email"][0]))
        self.assertEqual(email.count("var(--brand"), 1)  # the hard-coded logo of the same colour stays a hex
        self.assertEqual(by["Email"][1]["colors_tokenized"], 1)
        html = read(gallery.build(self.ws, sc)[0])
        self.assertIn('"c":"--brand"', html)
        self.assertIn('"tsvg":', html)
        again = tokens.run_file(self.ws, self.q["FAKEkeyAAA1"], VARS, fake_figma.TOKEN, log=QUIET)
        self.assertEqual(again["screens"], res["screens"])  # resumable: nothing redone

    def test_imports(self):
        import json as _json
        from kit import variables
        src = os.path.join(self.tmp, "mcp.json")
        with open(src, "w", encoding="utf-8") as f:
            _json.dump(_json.dumps(fake_figma.VARIABLES["FAKEkeyAAA1"]), f)  # some clients return a JSON string
        self.assertEqual(variables.import_path(self.ws, self.q["FAKEkeyCCC3"], src), ("mcp", 3))
        self.assertEqual(variables.status(self.ws, self.q["FAKEkeyCCC3"])["source"], "mcp")
        z = os.path.join(self.tmp, "Colors.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("Light.tokens.json", "{}")
            zf.writestr("Dark.tokens.json", "{}")
        self.assertEqual(variables.import_path(self.ws, self.q["FAKEkeyAAA1"], z), ("native", 2))
        self.assertTrue(variables.status(self.ws, self.q["FAKEkeyAAA1"])["native"])

    def test_library_variable_resolves_by_key(self):
        from kit import variables
        variables.from_rest(self.ws, self.q["FAKEkeyAAA1"], fake_figma.TOKEN, log=QUIET)
        VARS = variables.load_all(self.ws, self.q.values())
        self.assertEqual(variables.resolve("VariableID:k11/77:1", VARS)["css"], "--brand")


class FakeMCP:
    """Stands in for Figma desktop's MCP server: one Code Connect notice, then code with a localhost asset link."""
    def __init__(self):
        self.timeout, self.calls = 0, []

    def tool(self, name, **args):
        self.calls.append((args["nodeId"], args["forceCode"]))
        if len(self.calls) == 1:
            return {"content": [{"type": "text", "text": "Code Connect: would you like to map this component?"}]}
        code = ("export default function F() { return <div className='bg-[var(--brand,#5a78dc)]' /> }\n"
                "SUPER CRITICAL: notes\nThese styles are contained in the design: Body: Font(family: 'Inter').")
        return {"content": [{"type": "text", "text": code}]}


class Handoff(Base):
    def setUp(self):
        super().setUp()
        pages = fake_figma.FILES["FAKEkeyAAA1"]["pages"]
        self.added = fake_figma.page("0:5", "Components", [
            fake_figma.frame("5:1", "Button", 200, 120, kind="COMPONENT_SET", children=[
                fake_figma.frame("5:2", "State=Default", 120, 40, kind="COMPONENT", fills=[fake_figma.paint("#5A78DC", "VariableID:1:1")]),
                fake_figma.frame("5:3", "State=Hover", 120, 40, kind="COMPONENT")]),
            fake_figma.frame("5:9", "Sign in [M]", 390, 844, children=[fake_figma.frame("5:10", "Button", 120, 40, kind="INSTANCE")]),
            fake_figma.frame("5:11", "Sign in [D]", 1440, 900)])
        self.added["children"][1]["children"][0]["componentId"] = "5:2"
        pages.append(self.added)
        fake_figma.COMPONENTS.update({"5:2": {"name": "State=Default", "componentSetId": "5:1"}})
        self.ws = make_ws(self.tmp, self.base, addons=["tokens", "handoff"])
        do_plan(self.ws)
        runner.run(self.ws, log=QUIET)
        self.q = {x["key"]: x for x in read_json(os.path.join(self.ws.station, "plan.json"))["queue"]}

    def tearDown(self):
        fake_figma.FILES["FAKEkeyAAA1"]["pages"].remove(self.added)
        fake_figma.COMPONENTS.clear()
        super().tearDown()

    def test_full_package(self):
        from kit import handoff, variables
        variables.from_rest(self.ws, self.q["FAKEkeyAAA1"], fake_figma.TOKEN, log=QUIET)
        mcp = FakeMCP()
        base, res = handoff.run(self.ws, self.q["FAKEkeyAAA1"], ["0:5"], "Onboarding dev", fake_figma.TOKEN, log=QUIET, mcp_client=mcp)
        self.assertEqual(res["code"], "3 / 3 frames")
        self.assertEqual(res["anatomy"], "1 component page")  # the Button set
        self.assertTrue(os.path.exists(os.path.join(base, "tokens", "tokens.css")))
        sc = read_json(os.path.join(base, "screens.json"))
        btn = next(s for s in sc["screens"] if s["name"] == "Button")
        stem = handoff.stem(self.ws, sc, btn)
        anat = read(os.path.join(base, "components", stem + ".html"))
        self.assertIn("<code>--brand</code>", anat)  # bound fill shown as its token
        self.assertIn("Used in", anat)               # filled by used-by
        mob = next(s for s in sc["screens"] if s["name"] == "Sign in [M]")
        page = read(os.path.join(base, "frames", handoff.stem(self.ws, sc, mob) + ".html"))
        self.assertIn("Responsive pair", page)
        self.assertIn("Components used", page)
        self.assertIn("export default function F()", page)
        self.assertIn('"det":"frames/', read(os.path.join(base, "index.html")))  # gallery links each frame page
        self.assertTrue(os.path.exists(os.path.join(base, "README.md")))
        self.assertFalse(os.path.exists(os.path.join(self.ws.backup, "Mobile App", "Onboarding", "frames")))  # backup untouched
        n = len(mcp.calls)
        handoff.run(self.ws, self.q["FAKEkeyAAA1"], ["0:5"], "Onboarding dev", fake_figma.TOKEN, log=QUIET, mcp_client=mcp)
        self.assertEqual(len(mcp.calls), n)  # resumable: code is not asked again

    def test_without_mcp_or_variables(self):
        from kit import handoff, mcp as m
        saved = m.URL
        m.URL = "http://127.0.0.1:9/mcp"  # nothing listens there
        try:
            base, res = handoff.run(self.ws, self.q["FAKEkeyAAA1"], ["0:5"], "x", fake_figma.TOKEN, log=QUIET)
        finally:
            m.URL = saved
        self.assertTrue(res["code"].startswith("skipped"))
        self.assertTrue(res["tokens"].startswith("skipped"))
        self.assertTrue(os.path.exists(os.path.join(base, "index.html")))
