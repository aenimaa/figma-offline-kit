"""Offline gallery (index.html) for one exported file: grid · location map · page tree · filters · viewer.

Self-contained: no CDN, relative links, works from disk or `python -m http.server`. The page itself is
templates/gallery.html; this module fills in the data."""
import datetime
import html
import json
import os
import re
from urllib.parse import quote

from .export import file_dir, target
from .names import clean, divider_label, lp
from .util import REPO, read_json, write_text

TEMPLATE = os.path.join(REPO, "templates", "gallery.html")
TAG = "Page"  # one tag for every page: the gallery hides tag chips when there's only one


def rel_url(base, path):
    r = os.path.relpath(path, base).replace(os.sep, "/")
    return "/".join(quote(p, safe="") for p in r.split("/"))


def figma_url(key, nid=None):
    return f"https://www.figma.com/design/{key}" + (f"?node-id={nid.replace(':', '-')}" if nid else "")


def page_layout(ws, sc):
    """Exported pages in Figma order; `div` = label of divider page(s) between this page and the previous one."""
    inv = read_json(os.path.join(ws.station, "inventory.json"), {"files": {}})
    allp = (inv["files"].get(sc["key"]) or {}).get("pages") or []
    order = {p["id"]: i for i, p in enumerate(allp)}
    used = [p for p in sc["pages"] if any(s["pid"] == p["id"] for s in sc["screens"])]
    used.sort(key=lambda p: order.get(p["id"], 10 ** 6))
    out, prev = [], None
    for p in used:
        div = None
        if prev is not None and p["id"] in order and prev["id"] in order:
            labels = [divider_label(q["name"]) for q in allp[order[prev["id"]] + 1:order[p["id"]]]]
            labels = [lab for lab in labels if lab is not None]
            if labels:
                div = next((lab for lab in labels if lab), "")
        out.append({"id": p["id"], "name": p["name"], "tag": TAG, "arch": 0, "div": div})
        prev = p
    return out


KIND_ORDER = ["color", "spacing", "radius", "size", "stroke", "type", "effect", "opacity",
              "text-style", "effect-style", "color-style"]


def token_data(ws, sc, base, items):
    """tokens-usage.json → compact token table + per-screen refs (tsvg, tu, ub, tc). [] if the add-on hasn't run."""
    from .tokens import tok_path, usage_path
    U = read_json(usage_path(ws, sc))
    if not U:
        return []
    table, idx = [], {}

    def ref(kind, css, figma, ds, val):
        k = (kind, css or "", figma)
        if k not in idx:
            idx[k] = len(table)
            table.append(dict({"k": kind, "c": css or "", "f": figma, "d": ds or ""}, **({"v": val} if val else {})))
        return idx[k]
    for s, d in zip(sc["screens"], items):
        r = U["screens"].get(s["id"])
        if not r:
            continue
        p = tok_path(ws, sc, s)
        if r.get("svg") == "ok" and os.path.exists(lp(p)):
            d["tsvg"] = rel_url(base, p)
            d["tc"] = r.get("colors_tokenized", 0)
        elif r.get("svg") == "raw" and d.get("svg"):
            d["tsvg"] = d["svg"]
            d["tc"] = 0
        tu = []
        for kind in sorted(r.get("tokens") or {}, key=lambda k: KIND_ORDER.index(k) if k in KIND_ORDER else 99):
            if kind.startswith("_"):
                continue
            for t in r["tokens"][kind]:
                tu.append([ref(kind, t.get("css") or t.get("class"), t["figma"], t.get("ds"), t.get("value")), t["count"]])
        d["tu"] = tu
        if r.get("unbound_colors"):
            d["ub"] = [[u["hex"], u["count"], u.get("layers") or []] for u in r["unbound_colors"]]
    return table


def build(ws, sc):
    base = file_dir(ws, sc)
    layout = page_layout(ws, sc)
    items, newest = [], 0
    for s in sc["screens"]:
        nm = clean(s["name"])
        d = {"n": s["n"], "id": s["id"], "name": nm, "type": s.get("type") or "FRAME", "tag": TAG, "page": s["page"],
             "pid": s["pid"], "section": s.get("section") or "", "x": s.get("x"), "y": s.get("y"),
             "w": s.get("w"), "h": s.get("h"), "fig": figma_url(sc["key"], s["id"])}
        if not nm:
            d["unn"] = 1
        for ext in ("png", "svg", "pdf"):
            p = target(ws, sc, s, ext)
            if os.path.exists(lp(p)):
                d[ext] = rel_url(base, p)
                newest = max(newest, os.path.getmtime(lp(p)))
        fp = os.path.join(base, "frames", os.path.splitext(os.path.basename(target(ws, sc, s, "png")))[0] + ".html")
        if os.path.exists(lp(fp)):  # dev handoff page for this frame
            d["det"] = rel_url(base, fp)
        if d.get("png") and s.get("scale") is not None and s["scale"] < 2:
            d["sc"] = s["scale"]
        items.append(d)
    if any("svg" in d for d in items):  # only judge empty frames once the SVG pass has run
        for d in items:
            if d.get("png") and "svg" not in d and "pdf" not in d:
                d["emp"] = 1
    empty = sum(1 for d in items if d.get("emp"))
    missing = sum(1 for d in items if "png" not in d and "svg" not in d)
    date = (datetime.datetime.fromtimestamp(newest) if newest else datetime.datetime.now()).strftime("%Y-%m-%d")
    sections = [dict({k: c.get(k) for k in ("id", "name", "page", "path", "x", "y", "w", "h")}, tag=TAG, pid=c.get("pid"))
                for c in sc.get("sections", [])]
    data = {"key": sc["key"], "tagOrder": [TAG] if items else [], "screens": items, "sections": sections,
            "pages": layout, "tk": token_data(ws, sc, base, items)}
    esc = html.escape
    vals = {
        "TITLE": esc(sc["name"]), "FOLDER": esc(sc["project"]), "DATE": date, "TOTAL": str(len(items)),
        "SUMMARY": f"{len(layout)} page{'s' if len(layout) != 1 else ''}",
        "MISSING": (f' &middot; <span class="warn">{missing} not exported</span>' if missing else "")
                   + (f' &middot; {empty} empty frame{"s" if empty != 1 else ""}' if empty else ""),
        "FIGMA": figma_url(sc["key"]), "KEY": esc(sc["key"]),
        "DATA": json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
    }
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    out = re.sub(r"@@(\w+)@@", lambda m: vals[m.group(1)], tpl)  # one pass: inserted values are never rescanned
    path = os.path.join(base, "index.html")
    write_text(lp(path), out)
    return path, len(items), missing
