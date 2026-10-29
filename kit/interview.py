"""The one-round interview: question list, answer validation, and the terminal version for people without an AI."""
import os

from . import VERSION, figapi
from .util import REPO, now_iso

ARCHIVE_WORDS = ["archive", "old", "deprecated", "unused", "trash"]

QUESTIONS = [
    {"id": "workspace", "type": "text", "default": os.path.join("~", "figma-backup"),
     "ask": "Which folder should hold the backup?",
     "help": "Pick a drive with room: a whole team can take 10 GB or more. The kit creates backup/, temp/ and workstation/ inside it."},
    {"id": "team", "type": "text", "default": None,
     "ask": "What should be backed up? Paste your team link, or links to one or more files (comma-separated).",
     "help": "Whole team: open the team in Figma's file browser and copy the address (…/files/team/1234567890/…). "
             "Single files: open each file and copy the address bar (…/design/<key>/…)."},
    {"id": "mode", "type": "choice", "default": "project",
     "ask": "How should the backup run?",
     "options": [{"value": "full", "label": "Full: everything in one go, to the end"},
                 {"value": "project", "label": "Project by project: pause after each project"},
                 {"value": "file", "label": "File by file: pause after each file"}]},
    {"id": "pages", "type": "choice", "default": "all-except-archive",
     "ask": "Which pages of each file should be exported?",
     "options": [{"value": "all-except-archive", "label": "All pages except archive pages"},
                 {"value": "named", "label": "Only pages with names I give"},
                 {"value": "pick", "label": "I pick the pages for each file after the plan"}]},
    {"id": "page_names", "type": "list", "default": [], "when": {"pages": "named"},
     "ask": "Which page names? (comma-separated, exact names)",
     "help": "Example: Ready for dev, Shipped"},
    {"id": "archive_words", "type": "list", "default": ARCHIVE_WORDS, "when": {"pages": "all-except-archive"},
     "ask": "Which words mark an archive page? (comma-separated)",
     "help": "A page whose name contains one of these words is listed in the report but not exported."},
    {"id": "formats", "type": "multi", "default": ["png", "svg"],
     "ask": "Which screen formats?",
     "help": "Screens Figma can't render as SVG get a PDF automatically.",
     "options": [{"value": "png", "label": "PNG images"}, {"value": "svg", "label": "SVG vectors (text stays text)"}]},
    {"id": "addons", "type": "multi", "default": ["coverage", "drift", "archives"],
     "ask": "Which extras?",
     "options": [{"value": "coverage", "label": "Coverage page: what the backup holds, file by file"},
                 {"value": "drift", "label": "Drift check: which files changed in Figma since the backup"},
                 {"value": "archives", "label": "Archives: one compressed file per project"},
                 {"value": "tokens", "label": "Design tokens: variables as CSS/SCSS, SVGs with token colours"},
                 {"value": "handoff", "label": "Dev handoff: code and specs for pages you pick (needs Figma desktop)"}]},
    {"id": "local_copies", "type": "choice", "default": "auto",
     "ask": "Local copies (.fig / .jam / .deck) from Figma desktop?",
     "help": "Figma allows about 40 a day before bot checks, so a big team takes several days.",
     "options": [{"value": "auto", "label": "Automatic: the AI saves them (needs desktop control)"},
                 {"value": "guided", "label": "Guided: the AI opens each file, I press Save local copy"},
                 {"value": "skip", "label": "Skip local copies"}]},
    {"id": "archive_format", "type": "choice", "default": "zip", "when": {"addons": "archives"},
     "ask": "Archive format?",
     "options": [{"value": "zip", "label": "zip (works everywhere)"},
                 {"value": "7z", "label": "7z (smaller, needs 7-Zip)"},
                 {"value": "rar", "label": "rar (needs WinRAR)"}]},
    {"id": "language", "type": "choice", "default": "en",
     "ask": "Language for reports and messages?",
     "options": [{"value": "en", "label": "English"}, {"value": "fa", "label": "فارسی (Persian)"}]},
]
BY_ID = {q["id"]: q for q in QUESTIONS}


def applies(q, answers):
    """A question with `when` is asked only if the earlier answer matches (or contains, for multi answers)."""
    for key, want in q.get("when", {}).items():
        got = answers.get(key, BY_ID[key]["default"])
        if (want not in got) if isinstance(got, list) else (got != want):
            return False
    return True


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [str(x).strip() for x in v if str(x).strip()]


def _inside(child, parent):
    """True if child is parent or below it. Paths on different drives are never inside each other."""
    try:
        return os.path.commonpath([os.path.normcase(child), os.path.normcase(parent)]) == os.path.normcase(parent)
    except ValueError:
        return False


def validate(answers, doctor=None):
    """Return (config, errors, warnings). `doctor` is the last doctor.json, used only for warnings."""
    errors, warnings, a = [], [], {}
    unknown = sorted(set(answers) - set(BY_ID))
    if unknown:
        warnings.append(f"ignored unknown answers: {', '.join(unknown)}")
    for q in QUESTIONS:
        v = answers.get(q["id"], q["default"])
        if q["type"] in ("list", "multi"):
            v = _as_list(v)
        elif isinstance(v, str):
            v = v.strip()
        if q["type"] in ("choice", "multi"):
            allowed = [o["value"] for o in q["options"]]
            bad = [x for x in (v if q["type"] == "multi" else [v]) if x not in allowed]
            if bad and applies(q, a):
                errors.append(f"{q['id']}: {', '.join(map(str, bad))} is not one of {', '.join(allowed)}")
        a[q["id"]] = v

    ws = os.path.abspath(os.path.expanduser(a["workspace"] or ""))
    if not a["workspace"]:
        errors.append("workspace: a folder is required")
    elif _inside(REPO, ws):
        errors.append("workspace: pick a folder outside the kit (not the kit folder or one of its parents)")
    elif _inside(ws, REPO) and not _inside(ws, os.path.join(REPO, "test-workspace")):
        warnings.append("workspace is inside the kit folder: keep it out of git (only test-workspace/ is ignored)")
    tid = figapi.team_id(a["team"])
    files = figapi.file_keys(a["team"])
    if tid and files:
        errors.append("team: give either a team link or file links, not both")
    elif not tid and not files:
        errors.append("team: paste a team link (it contains /team/<number>) or file links (they contain /design/<key>)")
    if a["pages"] == "named" and not a["page_names"]:
        errors.append("page_names: give at least one page name, or choose another page rule")
    if not a["formats"]:
        errors.append("formats: choose png, svg or both")

    caps = (doctor or {}).get("ai", {})
    tools = (doctor or {}).get("tools", {})
    if a["local_copies"] == "auto" and caps.get("desktop-control") == "no":
        warnings.append("local_copies is automatic, but the AI said it has no desktop control: it will fall back to guided")
    if "archives" in a["addons"] and a["archive_format"] in ("7z", "rar") and tools and not tools.get(a["archive_format"]):
        warnings.append(f"{a['archive_format']} tool not found: archives will be zip until it is installed")
    if "handoff" in a["addons"] and (doctor or {}).get("checks", {}).get("desktop_mcp", {}).get("status") not in (None, "ok"):
        warnings.append("dev handoff needs Figma desktop's MCP server, which doctor could not reach yet")

    config = {
        "kit_version": VERSION,
        "created": now_iso(),
        "workspace": ws,
        "team": {"url": a["team"], "id": tid},
        "files": [] if tid else files,
        "mode": a["mode"],
        "pages": {"rule": a["pages"], "names": a["page_names"] if a["pages"] == "named" else [],
                  "archive_words": a["archive_words"] if a["pages"] == "all-except-archive" else []},
        "formats": a["formats"],
        "addons": {k: k in a["addons"] for k in ("coverage", "drift", "archives", "tokens", "handoff")},
        "local_copies": a["local_copies"],
        "archive_format": a["archive_format"] if "archives" in a["addons"] else "none",
        "language": a["language"],
    }
    return config, errors, warnings


def render_md():
    out = ["# Interview", "", "Ask all of these in one message. Defaults are in brackets.", ""]
    for i, q in enumerate(QUESTIONS, 1):
        cond = "".join(f" (only if {k} = {v})" for k, v in q.get("when", {}).items())
        d = q["default"]
        d = ", ".join(d) if isinstance(d, list) else d
        out.append(f"{i}. **{q['ask']}**{cond}  `{q['id']}`" + (f"  [{d}]" if d else ""))
        if q.get("help"):
            out.append(f"   {q['help']}")
        for o in q.get("options", []):
            out.append(f"   - `{o['value']}`: {o['label']}")
    return "\n".join(out)


def ask_terminal(inp=input):
    """The same interview in a terminal. Returns the answers dict."""
    answers = {}
    for q in QUESTIONS:
        if not applies(q, answers):
            continue
        print(f"\n{q['ask']}")
        if q.get("help"):
            print(f"  {q['help']}")
        opts = q.get("options", [])
        for n, o in enumerate(opts, 1):
            print(f"  {n}. {o['label']}")
        d = q["default"]
        shown = ", ".join(d) if isinstance(d, list) else (d or "")
        raw = inp(f"> [{shown}] " if shown else "> ").strip()
        if not raw:
            answers[q["id"]] = d
            continue
        if opts:  # accept option numbers or values
            picks = [p.strip() for p in raw.split(",")]
            vals = [opts[int(p) - 1]["value"] if p.isdigit() and 0 < int(p) <= len(opts) else p for p in picks]
            answers[q["id"]] = vals if q["type"] == "multi" else vals[0]
        else:
            answers[q["id"]] = raw
    return answers
