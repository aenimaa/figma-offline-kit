"""Rebuild examples/demo/ from the fake Figma team (no real data): python -m tests.make_demo"""
import os
import shutil
import tempfile

from kit import close, figapi, gallery, runner, tokens, variables
from kit.export import screens_path
from kit.util import read_json
from kit.util import REPO
from tests import fake_figma
from tests.test_m2 import QUIET, do_plan, make_ws


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
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
