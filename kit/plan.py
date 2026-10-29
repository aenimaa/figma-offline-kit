"""Plan: scan the team (projects → files → pages), choose pages by the interview rule, estimate the work.

Writes workstation/inventory.json (what Figma has), pages.json (which pages to export; the user may edit the
"export" values and they are kept on the next plan) and plan.json (the ordered work queue)."""
import hashlib
import json
import math
import os

from . import figapi
from .names import divider_label, norm, safe
from .util import now_iso, read_json, write_json

SCREEN_TYPES = ("FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE", "GROUP", "SECTION")
SCREENS_PER_MIN = {2: 10, 1: 15}  # rough export speed seen on a real team (PNG + SVG, or one format)
MB_PER_SCREEN = {"png": 0.4, "svg": 0.25}
SAVES_PER_DAY = 40


def scan(ws, token, log=print):
    """Inventory of the whole team. Files whose lastModified hasn't changed are not fetched again."""
    cfg = ws.config()
    path = os.path.join(ws.station, "inventory.json")
    inv = read_json(path, {"files": {}})
    seen = set()
    inv.update(scanned=now_iso(), projects=[])
    for pr, files in _sources(cfg, token, log):
        inv["projects"].append({"id": str(pr["id"]), "name": pr["name"], "files": [f["key"] for f in files]})
        for fl in files:
            k = fl["key"]
            seen.add(k)
            prev = inv["files"].get(k)
            base = {"key": k, "name": fl["name"], "project": pr["name"], "project_id": str(pr["id"]),
                    "last_modified": fl.get("last_modified")}
            if prev and prev.get("last_modified") == base["last_modified"] and "pages" in prev:
                prev.update(base)
                continue
            rec = dict(base)
            try:
                d = figapi.get(f"/v1/files/{k}?depth=2", token, log=log)
                rec["editorType"] = d.get("editorType", "figma")
                rec["version"] = d.get("version")
                rec["pages"] = []
                for p in d.get("document", {}).get("children", []):
                    cnt = {}
                    for c in p.get("children", []):
                        cnt[c["type"]] = cnt.get(c["type"], 0) + 1
                    rec["pages"].append({"id": p["id"], "name": p["name"], "counts": cnt})
            except figapi.FigmaError as e:
                rec["error"] = f"{e.status}: {e.body[:200]}"
            inv["files"][k] = rec
            log(f"  {pr['name'][:24]:24} | {rec.get('editorType', '?'):7} | {len(rec.get('pages', [])):3} pages | {fl['name']}")
            write_json(path, inv)  # save as we go: a long scan can be resumed
    for k, r in inv["files"].items():
        r["gone"] = k not in seen
    write_json(path, inv)
    return inv


def _sources(cfg, token, log):
    """(project, [file stubs]) pairs: from the team, or from the file links given in the interview."""
    tid = cfg["team"]["id"]
    if tid:
        team = figapi.get(f"/v1/teams/{tid}/projects", token, log=log)
        for pr in team.get("projects", []):
            yield pr, figapi.get(f"/v1/projects/{pr['id']}/files", token, log=log).get("files", [])
        return
    groups = {}
    for k in cfg.get("files", []):
        d = figapi.get(f"/v1/files/{k}?depth=1", token, log=log)
        folder = "Files"
        try:  # the project (folder) name, if the token may read file metadata
            folder = figapi.get(f"/v1/files/{k}/meta", token, tries=2, log=log).get("file", {}).get("folder_name") or folder
        except (figapi.FigmaError, RuntimeError, OSError):
            pass
        groups.setdefault(folder, []).append({"key": k, "name": d.get("name", k), "last_modified": d.get("lastModified")})
    for i, (folder, files) in enumerate(groups.items()):
        yield {"id": f"links-{i}", "name": folder}, files


def choose_pages(cfg, inv, old):
    """Apply the page rule to every design file. Existing decisions in pages.json are kept."""
    rule = cfg["pages"]["rule"]
    names = {norm(n) for n in cfg["pages"].get("names", [])}
    words = [w.casefold() for w in cfg["pages"].get("archive_words", [])]
    out = {}
    for k, f in inv["files"].items():
        if f.get("gone") or f.get("editorType") != "figma" or "pages" not in f:
            continue
        prev = (old.get(k) or {}).get("pages", {})
        pages = {}
        for p in f["pages"]:
            if p["id"] in prev and prev[p["id"]].get("why") == "you":
                pages[p["id"]] = dict(prev[p["id"]], name=p["name"])
                continue
            if p["id"] in prev and prev[p["id"]].get("export") is not None and prev[p["id"]].get("export") != prev[p["id"]].get("rule"):
                pages[p["id"]] = dict(prev[p["id"]], name=p["name"], why="you")  # the user changed it by hand
                continue
            if divider_label(p["name"]) is not None:
                exp, why = False, "divider"
            elif rule == "named":
                exp, why = norm(p["name"]) in names, "named" if norm(p["name"]) in names else "not named"
            elif rule == "all-except-archive":
                arch = any(w in p["name"].casefold() for w in words)
                exp, why = not arch, "archive" if arch else "rule"
            else:  # pick
                exp, why = None, "pick"
            pages[p["id"]] = {"name": p["name"], "export": exp, "rule": exp, "why": why}
        out[k] = {"file": f["name"], "project": f["project"], "pages": pages}
    return out


def page_estimate(counts):
    """Rough screen count for a page: its top-level frames, plus ≈ 6 screens per section (their content is unknown)."""
    return sum(v for t, v in counts.items() if t in SCREEN_TYPES and t != "SECTION") + 6 * counts.get("SECTION", 0)


def pages_hash(sel):
    """Fingerprint of the page choices: the run only starts once the user has confirmed exactly these."""
    flat = {k: {pid: p["export"] for pid, p in v["pages"].items()} for k, v in sel.items()}
    return hashlib.sha1(json.dumps(flat, sort_keys=True).encode()).hexdigest()[:12]


def _dirs(inv):
    """Backup folder per file: <project>/<file>, made unique when two files share a name."""
    used, out = {}, {}
    for k, f in sorted(inv["files"].items(), key=lambda kv: (kv[1]["project"], kv[1]["name"], kv[0])):
        d = os.path.join(safe(f["project"]), safe(f["name"]))
        if d.casefold() in used:
            d = os.path.join(safe(f["project"]), safe(f["name"], 48) + f" [{k[:6]}]")
        used[d.casefold()] = k
        out[k] = d
    return out


def build(ws, inv):
    cfg = ws.config()
    pages_path = os.path.join(ws.station, "pages.json")
    sel = choose_pages(cfg, inv, read_json(pages_path, {}))
    write_json(pages_path, sel)
    dirs = _dirs(inv)
    order = {p["id"]: i for i, p in enumerate(inv["projects"])}
    queue, undecided = [], 0
    for k, f in sorted(inv["files"].items(), key=lambda kv: (order.get(kv[1]["project_id"], 99), kv[1]["name"].casefold())):
        if f.get("gone"):
            continue
        item = {"key": k, "name": f["name"], "project": f["project"], "dir": dirs[k],
                "editorType": f.get("editorType", "?"), "last_modified": f.get("last_modified"), "pages": [], "est": 0}
        if f.get("error"):
            item["error"] = f["error"]
        if k in sel:
            pid_counts = {p["id"]: p["counts"] for p in f["pages"]}
            for pid, p in sel[k]["pages"].items():
                if p["export"] is None:
                    undecided += 1
                if p["export"]:
                    item["pages"].append(pid)
                    item["est"] += page_estimate(pid_counts.get(pid, {}))
        queue.append(item)
    nfmt = len(cfg["formats"])
    screens = sum(q["est"] for q in queue)
    copies = 0 if cfg["local_copies"] == "skip" else sum(1 for q in queue if q["editorType"] in ("figma", "figjam", "slides", "make"))
    plan = {"created": now_iso(), "queue": queue, "undecided_pages": undecided, "pages_hash": pages_hash(sel),
            "totals": {"projects": len(inv["projects"]), "files": len(queue),
                       "design_files": sum(1 for q in queue if q["editorType"] == "figma"),
                       "files_with_pages": sum(1 for q in queue if q["pages"]),
                       "pages": sum(len(q["pages"]) for q in queue), "screens_est": screens,
                       "minutes_est": math.ceil(screens / SCREENS_PER_MIN[min(nfmt, 2)]),
                       "gb_est": round(screens * sum(MB_PER_SCREEN[f] for f in cfg["formats"]) / 1024, 1),
                       "local_copies": copies, "copy_days": math.ceil(copies / SAVES_PER_DAY) if copies else 0}}
    write_json(os.path.join(ws.station, "plan.json"), plan)
    return plan, sel


def render(plan, sel, cfg):
    t = plan["totals"]
    hrs = f"{t['minutes_est'] / 60:.1f} h" if t["minutes_est"] >= 90 else f"{t['minutes_est']} min"
    lines = ["# Plan", "", f"Made {plan['created']}. Numbers marked ≈ are estimates.", "",
             "| | |", "|---|---|",
             f"| Projects | {t['projects']} |",
             f"| Files | {t['files']} ({t['design_files']} design files) |",
             f"| Pages to export | {t['pages']} in {t['files_with_pages']} files |",
             f"| Screens | ≈ {t['screens_est']} |",
             f"| Export time | ≈ {hrs} (automatic, runs on its own) |",
             f"| Size | ≈ {t['gb_est']} GB |"]
    if cfg["local_copies"] != "skip":
        how = "automatic" if cfg["local_copies"] == "auto" else "guided: you press Save for each file"
        lines.append(f"| Local copies | {t['local_copies']} files, ≈ {t['copy_days']} day(s) at ≈ {SAVES_PER_DAY} a day ({how}) |")
    lines.append("")
    if plan["undecided_pages"]:
        lines += [f"**Choose pages first:** {plan['undecided_pages']} pages have no decision yet: `python kit.py pages`.", ""]
    lines += ["## Per project", "", "| Project | File | Type | Pages exported | Skipped pages | Screens ≈ |", "|---|---|---|---|---|---|"]
    for q in plan["queue"]:
        p = sel.get(q["key"], {}).get("pages", {})
        skipped = [f"{v['name']} ({v['why']})" for v in p.values() if v["export"] is False and v["why"] != "divider"]
        kind = q["editorType"] + (" · error: " + q["error"][:60] if q.get("error") else "")
        lines.append(f"| {q['project']} | {q['name']} | {kind} | {len(q['pages'])} | {', '.join(skipped)[:160] or '—'} | {q['est'] or '—'} |")
    lines += ["", "Change pages with `python kit.py pages`. Your choices are kept when you plan again."]
    return "\n".join(lines) + "\n"
