"""Doctor: check the machine, the token, Figma desktop and the AI's own abilities, then say what the kit can do
and what the user still needs to do. Never prints the token."""
import os
import platform
import shutil
import sys

from . import figapi, mcp
from .util import now_iso, write_json

OK, MISSING, WARN, UNKNOWN = "ok", "missing", "warn", "unknown"

TOKEN_STEPS = [
    "In Figma, open Settings (your avatar, top-left) → Security → Personal access tokens → Generate new token.",
    "Tick these read scopes: current_user:read, file_content:read, file_metadata:read, folders:read "
    "(or projects:read on older token pages); add file_variables:read only on an Enterprise plan. "
    "Set an expiry you're comfortable with.",
    "Copy the token and paste it after FIGMA_TOKEN= in {env}. Save the file. Don't paste it in chat.",
]


def _check(status, detail, required=False, fix=None):
    return {"status": status, "detail": detail, "required": required, "fix": fix or []}


def figma_desktop_path():
    sysname = platform.system()
    cands = []
    if sysname == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        cands = [os.path.join(local, "Figma", "Figma.exe"), os.path.join(local, "Figma", "app.exe")]
    elif sysname == "Darwin":
        cands = ["/Applications/Figma.app", os.path.expanduser("~/Applications/Figma.app")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return shutil.which("figma") or shutil.which("figma-linux")


def find_tool(names, win_paths=()):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    if platform.system() == "Windows":
        for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
            for rel in win_paths:
                p = os.path.join(base, rel)
                if base and os.path.exists(p):
                    return p
    return None


def parse_ai(arg):
    """'desktop-control=yes,figma-mcp=no' → {'desktop-control': 'yes', 'figma-mcp': 'no'}."""
    out = {}
    for part in (arg or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            v = v.strip().lower()
            out[k.strip().lower()] = "yes" if v in ("yes", "y", "true", "1") else "no" if v in ("no", "n", "false", "0") else "unknown"
    return out


def run(ws=None, ai=None, network=True):
    ai = ai or {}
    cfg = ws.config() if ws and ws.exists() else None
    c, tools = {}, {}

    v = sys.version_info
    c["python"] = _check(OK if v >= (3, 10) else MISSING, f"Python {v.major}.{v.minor}.{v.micro}", True,
                         ["Install Python 3.10 or newer from https://www.python.org/downloads/"])

    if ws is None:
        c["workspace"] = _check(UNKNOWN, "no workspace chosen yet", True,
                                ["Answer the interview (python kit.py questions → python kit.py init)."])
    elif not ws.exists():
        c["workspace"] = _check(MISSING, f"{ws.root} has not been set up", True,
                                ["Run python kit.py init to create it."])
    else:
        free = shutil.disk_usage(ws.root).free / 2**30
        writable = os.access(ws.station, os.W_OK)
        status = OK if writable and free >= 5 else WARN if writable else MISSING
        c["workspace"] = _check(status, f"{ws.root} · {free:.1f} GB free" + ("" if writable else " · not writable"), True,
                                ["Free some space or choose a folder on a bigger drive (a team can take 10 GB or more)."]
                                if writable else ["Choose a folder you can write to and run init again."])

    if network:
        up, why = figapi.reachable()
        c["network"] = _check(OK if up else MISSING, "api.figma.com reachable" if up else f"api.figma.com not reachable ({why})",
                              True, ["Check your internet connection or VPN / proxy, then run doctor again."])
    else:
        c["network"] = _check(UNKNOWN, "skipped (--offline)", True)

    token, source = figapi.read_token(ws)
    env_hint = ws.env_path if ws else "workstation/.env in your workspace (created by init)"
    steps = [s.format(env=env_hint) for s in TOKEN_STEPS]
    if not token:
        c["token"] = _check(MISSING, "no Figma token found", True, steps)
    elif c["network"]["status"] != OK:
        c["token"] = _check(UNKNOWN, f"found in {source}, not tested (no network)", True)
    else:
        try:
            me = figapi.get("/v1/me", token, tries=2, timeout=20, log=lambda m: None)
            c["token"] = _check(OK, f"works (signed in as {me.get('handle', '?')}), from {source}", True)
        except figapi.FigmaError as e:
            c["token"] = _check(MISSING, f"Figma refused the token ({e.status}), from {source}", True,
                                ["The token is wrong, expired, or lacks the current_user:read scope. Make a new one:"] + steps)
        except Exception as e:  # noqa: BLE001
            c["token"] = _check(UNKNOWN, f"could not test the token ({str(e)[:80]})", True)

    if cfg and c["token"]["status"] == OK and not cfg["team"]["id"]:
        ok, bad = [], []
        for k in cfg.get("files", []):
            try:
                ok.append(figapi.get(f"/v1/files/{k}?depth=1", token, tries=2, timeout=60, log=lambda m: None).get("name", k))
            except figapi.FigmaError as e:
                bad.append(f"{k} ({e.status})")
            except Exception as e:  # noqa: BLE001
                bad.append(f"{k} ({str(e)[:40]})")
        c["team"] = _check(MISSING if bad else OK, (f"can't read: {', '.join(bad)}" if bad else
                           f"{len(ok)} file(s) readable: {', '.join(ok)[:120]}"), True,
                           ["Check the file links, that your account can open those files, "
                            "and that the token has the file_content:read scope. Then run doctor again."])
    elif cfg and c["token"]["status"] == OK:
        tid = cfg["team"]["id"]
        try:
            projects = figapi.get(f"/v1/teams/{tid}/projects", token, tries=2, timeout=30, log=lambda m: None)
            n = len(projects.get("projects", []))
            c["team"] = _check(OK, f"team {projects.get('name', tid)} · {n} projects visible", True)
        except figapi.FigmaError as e:
            c["team"] = _check(MISSING, f"can't read team {tid} ({e.status})", True,
                               ["Check the team link, that your account is a member of the team, "
                                "and that the token has the folders:read (or projects:read) scope. Then run doctor again."])
        except Exception as e:  # noqa: BLE001
            c["team"] = _check(UNKNOWN, f"could not check the team ({str(e)[:80]})", True)
    else:
        c["team"] = _check(UNKNOWN, "checked once the token works and the interview is done", True)

    app = figma_desktop_path()
    c["figma_desktop"] = _check(OK if app else MISSING, app or "Figma desktop app not found", False,
                                ["Install Figma desktop from https://www.figma.com/downloads/ and sign in "
                                 "(needed for local .fig copies and dev handoff)."])

    up, info = mcp.probe()
    c["desktop_mcp"] = _check(OK if up else MISSING,
                              f"answering · {len(info)} tools" if up else "not answering at http://127.0.0.1:3845/mcp",
                              False, ["Open Figma desktop and a design file, then turn on its local (desktop) MCP server. Where the switch "
                                      "lives changes between Figma versions (Preferences, or the Dev Mode inspect panel); some "
                                      "versions only offer remote MCP clients, and then the handoff's code step is skipped. "
                                      "Needed only for dev handoff."])

    dc = ai.get("desktop-control", "unknown")
    c["desktop_control"] = _check(OK if dc == "yes" else MISSING if dc == "no" else UNKNOWN,
                                  {"yes": "the AI can control the desktop", "no": "the AI has no desktop control",
                                   "unknown": "the AI has not said (doctor --ai desktop-control=yes|no)"}[dc], False,
                                  ["Use an AI app with desktop control (computer use) for automatic .fig "
                                   "copies. Without it, copies are guided: you press Save for each file."])
    fm = ai.get("figma-mcp", "unknown")
    c["figma_mcp"] = _check(OK if fm == "yes" else MISSING if fm == "no" else UNKNOWN,
                            {"yes": "the AI has Figma's MCP (use_figma)", "no": "the AI has no Figma MCP",
                             "unknown": "the AI has not said (doctor --ai figma-mcp=yes|no)"}[fm], False,
                            ["Connect Figma's MCP server to your AI to read variables without Enterprise. "
                             "Without it, variables are exported by hand (Variables panel → Export modes)."])

    tools["7z"] = find_tool(["7z", "7zz", "7za"], [os.path.join("7-Zip", "7z.exe")])
    tools["rar"] = find_tool(["rar"], [os.path.join("WinRAR", "Rar.exe")])
    tools["node"] = find_tool(["node"])
    for name, label, use in (("7z", "7-Zip", "smaller .7z archives"), ("rar", "WinRAR", ".rar archives"),
                             ("node", "Node.js", "accessibility checks of the gallery")):
        c[f"tool_{name}"] = _check(OK if tools[name] else MISSING, tools[name] or f"{label} not found", False,
                                   [f"Install {label} for {use}."])

    result = {"checked": now_iso(), "platform": f"{platform.system()} {platform.release()}",
              "ai": {"desktop-control": dc, "figma-mcp": fm}, "tools": tools, "checks": c,
              "can": can_do(c, cfg), "core_ready": all(c[k]["status"] == OK for k in c if c[k]["required"])}
    if ws and ws.exists():
        write_json(ws.doctor_path, result)
    return result


def can_do(c, cfg=None):
    ok = lambda k: c[k]["status"] == OK  # noqa: E731
    core = all(ok(k) for k in c if c[k]["required"])
    out = []
    out.append(("yes" if core else "no", "Back up every screen as PNG/SVG with an offline gallery (Figma REST API)"))
    if ok("figma_desktop") and ok("desktop_control"):
        out.append(("yes", "Save local copies (.fig/.jam/.deck) automatically, paced ≈ 40 a day"))
    elif ok("figma_desktop"):
        out.append(("partly", "Save local copies guided: I open each file, you press Save local copy"))
    else:
        out.append(("no", "Save local copies (needs Figma desktop)"))
    if ok("figma_mcp"):
        out.append(("yes", "Export variables / design tokens through Figma's MCP"))
    elif ok("figma_desktop"):
        out.append(("partly", "Export variables: by REST on Enterprise, otherwise guided native export"))
    else:
        out.append(("partly", "Export variables: by REST on Enterprise plans only"))
    out.append(("yes" if ok("desktop_mcp") else "no", "Dev handoff packages (code and specs) through Figma desktop's MCP"))
    fmt = "zip" + (", 7z" if ok("tool_7z") else "") + (", rar" if ok("tool_rar") else "")
    out.append(("yes", f"Archives ({fmt})"))
    return out


SYMBOL = {OK: "✔", MISSING: "✖", WARN: "!", UNKNOWN: "?"}
LABELS = {"python": "Python", "workspace": "Workspace", "network": "Network", "token": "Figma token",
          "team": "Figma team / files", "figma_desktop": "Figma desktop", "desktop_mcp": "Figma desktop MCP",
          "desktop_control": "AI desktop control", "figma_mcp": "AI Figma MCP", "tool_7z": "7-Zip",
          "tool_rar": "WinRAR", "tool_node": "Node.js"}


def render(r):
    c = r["checks"]
    lines = ["# Doctor", "", f"Checked {r['checked']} on {r['platform']}.", ""]
    lines.append("| | Check | Result |")
    lines.append("|---|---|---|")
    for k, v in c.items():
        lines.append(f"| {SYMBOL[v['status']]} | {LABELS.get(k, k)}{'' if v['required'] else ' (optional)'} | {v['detail']} |")
    lines += ["", "## I can do", ""]
    for state, text in r["can"]:
        lines.append(f"- {'✔' if state == 'yes' else '◐' if state == 'partly' else '✖'} {text}")
    todo = [(k, v) for k, v in c.items() if v["status"] != OK and v["fix"]]
    req = [(k, v) for k, v in todo if v["required"]]
    opt = [(k, v) for k, v in todo if not v["required"]]
    lines += ["", "## You need to do", ""]
    if not req:
        lines.append("Nothing required. The backup can start.")
    for k, v in req:
        lines.append(f"**{LABELS.get(k, k)}**: {v['detail']}")
        lines += [f"{i}. {s}" for i, s in enumerate(v["fix"], 1)]
        lines.append("")
    if opt:
        lines += ["### Optional (each one switches a feature on)", ""]
        for k, v in opt:
            lines.append(f"- **{LABELS.get(k, k)}**: {' '.join(v['fix'])}")
    return "\n".join(lines).rstrip() + "\n"
