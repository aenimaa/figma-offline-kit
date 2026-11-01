"""Screens: list the frames on each chosen page, then export them as PNG / SVG through Figma's REST API.

A screen is a top-level FRAME / COMPONENT / COMPONENT_SET / INSTANCE / GROUP; sections are opened, nested too.
Resumable: anything already on disk is skipped. Screen numbers stay stable across re-runs."""
import os
import time
import urllib.request

from . import figapi
from .names import clean, lp, safe
from .util import read_json, write_json

SCREEN = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE", "GROUP"}
MAX_PX = 16e6                            # Figma's renderer times out on huge renders: keep each PNG ≤ 16 Mpx
BUDGET = {"png": 48e6, "svg": 24e6, "pdf": 24e6}   # pixels per request
PER_CALL = {"png": 25, "svg": 10, "pdf": 10}


Stopped = figapi.Stopped  # the person asked to pause



def screens_path(ws, key):
    return os.path.join(ws.station, "screens", key + ".json")


def _box(n):
    bb = n.get("absoluteBoundingBox") or {}
    return {"x": round(bb.get("x", 0)), "y": round(bb.get("y", 0)), "w": round(bb.get("width", 0)), "h": round(bb.get("height", 0))}


def _walk(node, path, out, sections, page):
    for c in node.get("children", []):
        if c["type"] == "SECTION":
            sections.append({"id": c["id"], "name": clean(c["name"]), "page": page["name"], "pid": page["id"],
                             "path": " / ".join(path + [clean(c["name"]) or "_"]), **_box(c)})
            _walk(c, path + [clean(c["name"]) or "_"], out, sections, page)
        elif c["type"] in SCREEN and c.get("visible", True):
            out.append({"id": c["id"], "name": c["name"], "type": c["type"], "page": page["name"], "pid": page["id"],
                        "section": " / ".join(path), **_box(c)})


def list_screens(ws, item, token, log=print):
    """Write workstation/screens/<key>.json for one file and return it."""
    inv = read_json(os.path.join(ws.station, "inventory.json"))
    names = {p["id"]: p["name"] for p in inv["files"][item["key"]]["pages"]}
    pages, used = [], set()
    for pid in item["pages"]:
        d = safe(names.get(pid, pid))
        if d.casefold() in used:
            d = safe(names.get(pid, pid), 48) + f" [{pid.replace(':', '-')}]"
        used.add(d.casefold())
        pages.append({"id": pid, "name": names.get(pid, pid), "dir": d})
    out, sections = [], []
    for p in pages:
        d = figapi.get(f"/v1/files/{item['key']}/nodes?ids={p['id']}&depth=6", token, log=log)
        node = (d.get("nodes", {}).get(p["id"]) or {}).get("document", {})
        _walk(node, [], out, sections, p)
    fp = screens_path(ws, item["key"])
    old = read_json(fp, {})
    keep = {s["id"]: s for s in old.get("screens", [])}
    nxt = max((s["n"] for s in keep.values()), default=0)
    for s in out:
        if s["id"] in keep:
            s["n"] = keep[s["id"]]["n"]
            if "scale" in keep[s["id"]]:
                s["scale"] = keep[s["id"]]["scale"]
        else:
            nxt += 1
            s["n"] = nxt
    out.sort(key=lambda s: s["n"])
    sc = {"key": item["key"], "name": item["name"], "project": item["project"], "dir": item["dir"],
          "last_modified": item.get("last_modified"), "pages": pages, "screens": out, "sections": sections}
    write_json(fp, sc)
    return sc


def file_dir(ws, sc):
    """The file's backup folder, or sc["base"] for exports elsewhere (dev handoff)."""
    return sc.get("base") or os.path.join(ws.backup, sc["dir"])


def target(ws, sc, s, ext):
    page = next((p["dir"] for p in sc["pages"] if p["id"] == s["pid"]), safe(s["page"]))
    sub = [page] + ([safe(x, 40) for x in s["section"].split(" / ")] if s["section"] else [])
    return os.path.join(file_dir(ws, sc), "screens", ext, *sub, f"{s['n']:03d} {safe(s['name'], 50)} [{s['id'].replace(':', '-')}].{ext}")


def scale_of(s):
    """@2x unless that renders more than MAX_PX; then the largest scale that fits (floored to 0.05, min 0.25)."""
    a = max(s.get("w", 1) * s.get("h", 1), 1)
    return 2.0 if a * 4 <= MAX_PX else max(0.25, int(((MAX_PX / a) ** 0.5) * 20) / 20)


def _fetch(url, path, tries=4):
    """Download one rendered image from Figma's image server. Every read has a deadline (figapi.read_all), so a
    stalled connection fails and is tried again instead of hanging; a pause request ends it within seconds."""
    err = None
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=figapi.IDLE_TIMEOUT) as r:
                data = figapi.read_all(r)
            os.makedirs(lp(os.path.dirname(path)), exist_ok=True)
            with open(lp(path), "wb") as f:
                f.write(data)
            return len(data)
        except Stopped:
            raise
        except Exception as e:  # noqa: BLE001
            err = e
            figapi.nap(3 * (t + 1))
    raise err


def _images(key, ids, ext, scale, token, tries, log):
    q = f"/v1/images/{key}?ids={','.join(ids)}&format={ext}"
    q += f"&scale={scale:g}" if ext == "png" else ("&svg_outline_text=false" if ext == "svg" else "")
    return figapi.get(q, token, tries=tries, log=log).get("images") or {}


def export(ws, sc, token, formats, log=print, stop=lambda: False):
    """Export every screen of one file in the given formats. Returns {"empty": [ids with no render at all]}."""
    key = sc["key"]
    by_id = {s["id"]: s for s in sc["screens"]}
    no_svg = []
    for ext in formats:
        todo = [s for s in sc["screens"] if not os.path.exists(lp(target(ws, sc, s, ext)))
                and not (ext == "svg" and os.path.exists(lp(target(ws, sc, s, "pdf"))))]
        log(f"  {ext}: {len(sc['screens']) - len(todo)} on disk, {len(todo)} to go")
        groups, cur, px, cur_scale = [], [], 0, None
        for s in sorted(todo, key=lambda s: (scale_of(s) if ext == "png" else 0, s["n"])):
            sc_ = scale_of(s) if ext == "png" else 1
            cost = s.get("w", 1) * s.get("h", 1) * sc_ * sc_
            if cur and (sc_ != cur_scale or px + cost > BUDGET[ext] or len(cur) >= PER_CALL[ext]):
                groups.append((cur_scale, cur))
                cur, px = [], 0
            cur.append(s)
            px += cost
            cur_scale = sc_
        if cur:
            groups.append((cur_scale, cur))
        done = 0
        for gscale, chunk in groups:
            if stop():
                raise Stopped()
            try:
                urls = _images(key, [s["id"] for s in chunk], ext, gscale, token, 3 if len(chunk) > 1 else 6, log)
            except (figapi.FigmaError, RuntimeError, OSError) as e:
                # heavy frames make Figma's renderer time out: go one by one; PNG may drop to half scale
                log(f"  batch failed ({str(e)[:50]}) → one by one")
                urls = {}
                for s in chunk:
                    for sc2 in ([gscale, max(0.25, gscale / 2)] if ext == "png" else [1]):
                        try:
                            urls.update(_images(key, [s["id"]], ext, sc2, token, 4, log))
                            if ext == "png" and sc2 != gscale:
                                by_id[s["id"]]["scale"] = sc2
                                log(f"  lower scale @{sc2:g}x: {clean(s['name'])}")
                            break
                        except (figapi.FigmaError, RuntimeError, OSError) as e2:
                            last = e2
                    else:
                        log(f"  no {ext} for {clean(s['name'])} ({str(last)[:80]})")
            for s in chunk:
                if stop():
                    raise Stopped()
                u = urls.get(s["id"])
                if u:
                    _fetch(u, target(ws, sc, s, ext))
                    if ext == "png" and gscale != 2 and "scale" not in by_id[s["id"]]:
                        by_id[s["id"]]["scale"] = gscale
                elif ext == "svg":
                    no_svg.append(s)
            done += len(chunk)
            log(f"  {ext} {done}/{len(todo)}" + (f" @{gscale:g}x" if ext == "png" and gscale != 2 else ""))
        if not sc.get("base"):
            write_json(screens_path(ws, key), sc)  # keep PNG scales
    # vector PDF where Figma's SVG render fails; a frame with neither is empty
    empty = []
    for s in no_svg:
        try:
            u = _images(key, [s["id"]], "pdf", 1, token, 3, log).get(s["id"])
        except (figapi.FigmaError, RuntimeError, OSError):
            u = None
        if u:
            _fetch(u, target(ws, sc, s, "pdf"))
            log(f"  PDF instead of SVG: {clean(s['name'])}")
        else:
            empty.append(s["id"])
    return {"empty": empty}
