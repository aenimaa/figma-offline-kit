"""Rebuild examples/demo/ from the fake Figma team (no real data): python -m tests.make_demo"""
import os
import shutil
import tempfile

from kit import close, figapi, gallery, handoff, runner, tokens, variables
from kit.export import screens_path
from kit.util import read_json, write_json
from kit.util import REPO
from tests import fake_figma
from tests.test_m2 import QUIET, do_plan, make_ws


class DemoMCP:
    """Stands in for Figma desktop's MCP server with plausible React + Tailwind output for the demo."""
    timeout = 0

    def tool(self, name, **args):
        title = {"2:1": "Welcome", "2:2": "EmailStep", "2:6": "EmailTaken", "2:3": "Home", "2:7": "Icons"}.get(args["nodeId"], "Screen")
        code = f"""export default function {title}() {{
  return (
    <div className="flex h-[844px] w-[390px] flex-col bg-white px-7 pb-10 pt-11">
      <h1 className="text-[28px] font-bold leading-tight text-[#1b1f2a]">{title.replace("Step", "")}</h1>
      <p className="mt-2 text-[15px] text-[#667085]">We'll send your plant reminders there.</p>
      <button className="mt-auto rounded-[14px] bg-[var(--brand,#5a78dc)] py-4 font-semibold text-white">
        Continue
      </button>
    </div>
  );
}}
SUPER CRITICAL: notes
These styles are contained in the design: Title: Font(family: "Segoe UI", style: Bold, size: 28), Body: Font(family: "Segoe UI", style: Regular, size: 15)."""
        return {"content": [{"type": "text", "text": code}]}


def main():
    srv, base = fake_figma.start()
    figapi.API, figapi.MIN_GAP = base, 0
    tmp = tempfile.mkdtemp()
    try:
        ws = make_ws(tmp, base, addons=["tokens", "coverage", "drift"])
        do_plan(ws)
        runner.run(ws, log=QUIET)
        queue = read_json(os.path.join(ws.station, "plan.json"))["queue"]
        for q in queue:
            variables.from_rest(ws, q, fake_figma.TOKEN, log=QUIET)
        VARS = variables.load_all(ws, queue)
        for q in queue:
            if q["pages"]:
                tokens.run_file(ws, q, VARS, fake_figma.TOKEN, log=QUIET)
                gallery.build(ws, read_json(screens_path(ws, q["key"])))
        close.drift(ws, fake_figma.TOKEN, log=QUIET)
        close.coverage(ws)
        out = os.path.join(REPO, "examples", "demo")
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(ws.backup, out)
        print("demo ->", out)
        onboarding = next(q for q in queue if q["key"] == "FAKEkeyAAA1")
        hbase, _ = handoff.run(ws, onboarding, ["0:3"], "Onboarding sign-up", fake_figma.TOKEN, log=QUIET, mcp_client=DemoMCP())
        hout = os.path.join(REPO, "examples", "handoff")
        shutil.rmtree(hout, ignore_errors=True)
        shutil.copytree(hbase, os.path.join(hout, os.path.basename(hbase)))
        sj = os.path.join(hout, os.path.basename(hbase), "screens.json")
        sc = read_json(sj)
        sc["base"] = "."  # the build folder was a temp path on this machine; never publish it
        write_json(sj, sc)
        print("handoff ->", hout)
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
