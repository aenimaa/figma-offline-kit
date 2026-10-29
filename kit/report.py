"""workstation/REPORT.md: one human-readable page, rebuilt section by section as the job moves on."""
import os
import re

from .util import write_text

ORDER = ["summary", "doctor", "config", "plan", "pages", "run", "copies", "tokens", "close"]
_SECTION = re.compile(r"<!-- kit:(\w+) -->\n(.*?)<!-- /kit:\1 -->\n?", re.S)


def update(ws, name, markdown):
    text = ""
    if os.path.exists(ws.report_path):
        with open(ws.report_path, encoding="utf-8") as f:
            text = f.read()
    parts = {m.group(1): m.group(2) for m in _SECTION.finditer(text)}
    # sections sit one level below the page title; shift only the new text (stored parts are already shifted)
    parts[name] = re.sub(r"^(#+) ", r"#\1 ", markdown.rstrip(), flags=re.M) + "\n"
    out = ["# Figma backup report\n", "This file is written by figma-offline-kit. Edits here are overwritten.\n"]
    for key in ORDER + sorted(set(parts) - set(ORDER)):
        if key in parts:
            out.append(f"<!-- kit:{key} -->\n{parts[key]}<!-- /kit:{key} -->\n")
    write_text(ws.report_path, "\n".join(out))


def config_md(cfg):
    p = cfg["pages"]
    pages = {"all-except-archive": f"all except archive pages (names containing: {', '.join(p['archive_words'])})",
             "named": f"only: {', '.join(p['names'])}", "pick": "picked per file after the plan"}[p["rule"]]
    addons = [k for k, v in cfg["addons"].items() if v] or ["none"]
    rows = [("Workspace", cfg["workspace"]), ("Source", f"team {cfg['team']['id']}" if cfg["team"]["id"] else f"{len(cfg.get('files', []))} file(s): " + ", ".join(cfg.get("files", []))),
            ("Mode", cfg["mode"]), ("Pages", pages), ("Formats", ", ".join(cfg["formats"])),
            ("Extras", ", ".join(addons)), ("Local copies", cfg["local_copies"]),
            ("Archives", cfg["archive_format"]), ("Language", cfg["language"])]
    return "# Settings\n\n| | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows) + "\n"
