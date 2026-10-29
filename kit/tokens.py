"""Token add-on for exported screens.

Per screen it writes a token report (variables and styles used, colours bound to nothing) and a token SVG: the same
picture with colours written as style="fill:var(--token, #hex)", so the hex stays as fallback. Hybrid, always exact:
  raw     no colour on the screen is bound to a variable → the raw SVG already is the token SVG (nothing written)
  hex     every bound colour's hex belongs to exactly one token on that screen → rewrite the raw SVG by hex
  render  some hex is shared by a token and something else → Figma re-renders with layer ids, rewrite per layer
Outputs per file: screens/svg-tokens/<same tree as svg>/… and tokens-usage.json. Never touches PNG / raw SVG / PDF.
Runs only while the file in Figma is still the state the backup shows (lastModified)."""
import os
import re
import time
import urllib.request
from collections import Counter, defaultdict

from . import figapi
from .export import file_dir, screens_path, target
from .names import lp
from .util import now_iso, read_json, write_json, write_text
from .variables import resolve, slug

SVG_Q = "&format=svg&svg_outline_text=false&svg_include_node_id=true"
KIND = {"fills": "color", "strokes": "color", "color": "color", "textRangeFills": "color", "effects": "effect",
        "itemSpacing": "spacing", "counterAxisSpacing": "spacing", "paddingLeft": "spacing", "paddingRight": "spacing",
        "paddingTop": "spacing", "paddingBottom": "spacing", "topLeftRadius": "radius", "topRightRadius": "radius",
        "bottomLeftRadius": "radius", "bottomRightRadius": "radius", "cornerRadius": "radius", "rectangleCornerRadii": "radius",
        "fontSize": "type", "fontWeight": "type", "fontFamily": "type", "lineHeight": "type", "letterSpacing": "type",
        "paragraphSpacing": "type", "fontStyle": "type", "width": "size", "height": "size", "minWidth": "size",
        "maxWidth": "size", "minHeight": "size", "maxHeight": "size", "strokeWeight": "stroke",
        "individualStrokeWeights": "stroke", "strokeTopWeight": "stroke", "strokeBottomWeight": "stroke",
        "strokeLeftWeight": "stroke", "strokeRightWeight": "stroke", "opacity": "opacity", "visible": "visibility",
        "characters": "content"}
_EL = re.compile(r"<(/?)([A-Za-z][\w:-]*)([^<>]*?)(/?)>")
_COL = re.compile(r'\s(fill|stroke)="(#[0-9A-Fa-f]{6})"')
_DEFS = {"defs", "clipPath", "mask", "pattern", "linearGradient", "radialGradient", "filter"}


def tok_path(ws, sc, s):
    raw = target(ws, sc, s, "svg")
    root = file_dir(ws, sc)
    rel = os.path.relpath(os.path.dirname(raw), os.path.join(root, "screens", "svg"))
    return os.path.join(root, "screens", "svg-tokens", rel, os.path.basename(raw))


def _hex(c, upper=True):
    h = "#" + "".join(f"{round(c[k] * 255):02x}" for k in "rgb")
    return h.upper() if upper else h


def _aliases(o):
    if isinstance(o, dict):
        if o.get("type") == "VARIABLE_ALIAS":
            yield o["id"]
        else:
            for v in o.values():
                yield from _aliases(v)
    elif isinstance(o, list):
        for v in o:
            yield from _aliases(v)


def usage(doc, VARS, styles):
    """{kind: [{css, figma, ds, count, value?}]} for every variable and style the screen uses; unknown ids under _unresolved."""
    hits, unresolved, sty = defaultdict(Counter), Counter(), defaultdict(Counter)

    def add(kind, vid):
        r = resolve(vid, VARS)
        if r:
            hits[kind][(r["css"], r["name"], r["ds"], r.get("hex"))] += 1
        else:
            unresolved[vid] += 1

    def walk(n):
        for prop, val in (n.get("boundVariables") or {}).items():
            for vid in _aliases(val):
                add(KIND.get(prop, prop), vid)
        for paint in (n.get("fills") or []) + (n.get("strokes") or []):
            for vid in _aliases(paint.get("boundVariables") or {}):
                add("color", vid)
        for kind, sid in (n.get("styles") or {}).items():
            st = styles.get(sid)
            if st:
                sty[{"text": "text-style", "effect": "effect-style", "fill": "color-style",
                     "stroke": "color-style"}.get(kind, kind)][st["name"]] += 1
        for c in n.get("children") or []:
            walk(c)

    walk(doc)
    out = {k: [dict({"css": c, "figma": f, "ds": d, "count": n}, **({"value": h} if h else {}))
               for (c, f, d, h), n in cnt.most_common()] for k, cnt in sorted(hits.items())}
    for k, cnt in sty.items():
        out[k] = [{"figma": f, "class": "text-" + slug(f.replace("/", "-")) if k == "text-style" else None, "count": n}
                  for f, n in cnt.most_common()]
    if unresolved:
        out["_unresolved"] = [{"id": i, "count": n} for i, n in unresolved.most_common()]
    return out


def unbound_colors(doc):
    """Visible solid fills/strokes with neither a variable nor a colour style → [{hex, count, layers}]."""
    hits, where = Counter(), defaultdict(list)

    def walk(n):
        if n.get("visible") is False:
            return
        st = n.get("styles") or {}
        for kind, key in (("fill", "fills"), ("stroke", "strokes")):
            if kind in st:
                continue
            for p in n.get(key) or []:
                if p.get("type") != "SOLID" or p.get("visible") is False or p.get("opacity", 1) == 0:
                    continue
                if (p.get("boundVariables") or {}).get("color"):
                    continue
                h = _hex(p["color"])
                hits[h] += 1
                if len(where[h]) < 3 and n.get("name") not in where[h]:
                    where[h].append(n.get("name"))
        for c in n.get("children") or []:
            walk(c)

    walk(doc)
    return [{"hex": h, "count": c, "layers": where[h]} for h, c in hits.most_common()]


def node_paints(doc, VARS):
    """[(kind, HEX, css|None)] for visible solid fills and strokes, in drawing order."""
    out = []

    def paints(n, kind, key):
        if kind == "stroke" and not (n.get("strokeWeight") or n.get("individualStrokeWeights")):
            return
        for p in n.get(key) or []:
            if p.get("type") != "SOLID" or p.get("visible") is False:
                continue
            vid = ((p.get("boundVariables") or {}).get("color") or {}).get("id")
            r = resolve(vid, VARS) if vid else None
            out.append((kind, _hex(p["color"]), r["css"] if r else None))

    def walk(n):
        if n.get("visible") is False:
            return
        paints(n, "fill", "fills")
        paints(n, "stroke", "strokes")
        for c in [] if n.get("type") == "BOOLEAN_OPERATION" else (n.get("children") or []):
            walk(c)

    walk(doc)
    return out


def _svg_colors(svg):
    out, skip = [], []
    for mt in _EL.finditer(svg):
        closing, tag, attrs, selfclose = mt.groups()
        if closing:
            if skip and skip[-1] == tag:
                skip.pop()
            continue
        if tag in _DEFS and not selfclose:
            skip.append(tag)
            continue
        if skip:
            continue
        for a in _COL.finditer(attrs):
            out.append((a.group(1), a.group(2).upper(), mt.start()))
    return out


def _rewrite(svg, by_el):
    out, pos = [], 0
    for mt in _EL.finditer(svg):
        if mt.start() not in by_el:
            continue
        _, tag, attrs, selfclose = mt.groups()
        st = ";".join(by_el[mt.start()])
        attrs = attrs.replace(' style="', ' style="' + st + ";", 1) if ' style="' in attrs else attrs + f' style="{st}"'
        out.append(svg[pos:mt.start()])
        out.append(f"<{tag}{attrs}{selfclose}>")
        pos = mt.end()
    out.append(svg[pos:])
    return "".join(out)


def tokenize_by_hex(svg, doc, VARS):
    """A hex owned by exactly one token on this screen (and never hard-coded there) is rewritten everywhere."""
    owners = defaultdict(set)
    for k, h, css in node_paints(doc, VARS):
        owners[(k, h)].add(css)
    safe = {kh: next(iter(v)) for kh, v in owners.items() if len(v) == 1 and None not in v}
    by_el, n = defaultdict(list), 0
    for k, h, start in _svg_colors(svg):
        css = safe.get((k, h))
        if css:
            by_el[start].append(f"{k}:var({css}, {h})")
            n += 1
    return (_rewrite(svg, by_el) if by_el else svg), n


def tokenize_rendered(svg, doc, VARS):
    """SVG rendered with data-node-id: rewrite a colour only where its layer's paint is bound and the hex matches."""
    pm = {}

    def walk(n):
        for kind, key in (("fill", "fills"), ("stroke", "strokes")):
            for p in n.get(key) or []:
                if p.get("type") == "SOLID" and p.get("visible", True):
                    vid = ((p.get("boundVariables") or {}).get("color") or {}).get("id")
                    r = resolve(vid, VARS) if vid else None
                    if r:
                        pm.setdefault(n["id"], {})[kind] = (r["css"], _hex(p["color"], upper=False))
                    break
        for c in n.get("children") or []:
            walk(c)

    walk(doc)
    out, pos, stack, rep = [], 0, [], 0
    for mt in _EL.finditer(svg):
        out.append(svg[pos:mt.start()])
        pos = mt.end()
        closing, tag, attrs, selfclose = mt.groups()
        if closing:
            if stack:
                stack.pop()
            out.append(mt.group(0))
            continue
        nid = re.search(r'data-node-id="([^"]+)"', attrs)
        node = nid.group(1) if nid else (stack[-1] if stack else None)
        styles = []
        for kind in ("fill", "stroke"):
            if node in pm and kind in pm[node]:
                css, hx = pm[node][kind]
                a = re.search(rf'\s{kind}="(#[0-9A-Fa-f]{{6}})"', attrs)
                if a and a.group(1).lower() == hx:
                    styles.append(f"{kind}:var({css}, {a.group(1)})")
                    rep += 1
        if styles:
            attrs = attrs.replace(' style="', ' style="' + ";".join(styles) + ";", 1) if ' style="' in attrs \
                else attrs + ' style="' + ";".join(styles) + '"'
        out.append(f"<{tag}{attrs}{selfclose}>")
        if not selfclose:
            stack.append(node)
    return "".join(out) + svg[pos:], rep


def _text(url, tries=4):
    err = None
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(3 * (t + 1))
    raise err


def usage_path(ws, sc):
    return os.path.join(file_dir(ws, sc), "tokens-usage.json")


def run_file(ws, item, VARS, token, log=print, sc=None):
    """Token report + token SVGs for one exported file (or the handoff subset `sc`). Resumable.
    Returns the summary, or {'changed': …} when Figma changed since the backup."""
    handoff = sc is not None
    sc = sc or read_json(screens_path(ws, item["key"]))
    up = usage_path(ws, sc)
    U = read_json(up) or {"about": "Design tokens per screen, made by figma-offline-kit. svg: raw = no colour bound to a "
                          "variable, the raw SVG is the token SVG · ok = token SVG in screens/svg-tokens (method hex or "
                          "render) · none = no SVG for this frame · gone = frame deleted in Figma since the backup.",
                          "file_key": item["key"], "file": sc["name"], "screens": {}}
    lm = figapi.get(f"/v1/files/{item['key']}?depth=1", token, log=log).get("lastModified")
    backed = None if handoff else ws.state().get("files", {}).get(item["key"], {}).get("last_modified")
    if backed and lm and lm > backed:
        return {"changed": lm}
    U["figma_last_modified"] = lm
    todo = [s for s in sc["screens"] if s["id"] not in U["screens"]
            or (U["screens"][s["id"]].get("svg") == "ok" and not os.path.exists(lp(tok_path(ws, sc, s))))]
    log(f"  {sc['name']}: {len(sc['screens']) - len(todo)} done, {len(todo)} to go")
    queue, docs = [], {}
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        nodes = figapi.get(f"/v1/files/{item['key']}/nodes?ids={','.join(s['id'] for s in chunk)}", token, log=log).get("nodes", {})
        for s in chunk:
            nd = nodes.get(s["id"])
            rec = {"n": s["n"]}
            if not nd:
                U["screens"][s["id"]] = dict(rec, svg="gone")
                continue
            doc = nd["document"]
            rec["tokens"] = usage(doc, VARS, nd.get("styles") or {})
            rec["unbound_colors"] = unbound_colors(doc)
            raw = target(ws, sc, s, "svg")
            owners = defaultdict(set)
            for k, h, css in node_paints(doc, VARS):
                owners[(k, h)].add(css)
            bound = [kh for kh, v in owners.items() if v - {None}]
            if not os.path.exists(lp(raw)):
                rec["svg"] = "none"
            elif not bound:
                rec.update(svg="raw", colors_tokenized=0)
            elif all(len(owners[kh]) == 1 for kh in bound):
                with open(lp(raw), encoding="utf-8") as f:
                    tsvg, n = tokenize_by_hex(f.read(), doc, VARS)
                write_text(lp(tok_path(ws, sc, s)), tsvg)
                rec.update(svg="ok", method="hex", colors_tokenized=n)
            else:
                docs[s["id"]] = (doc, rec)
                queue.append(s)
                continue
            U["screens"][s["id"]] = rec
        write_json(up, U)
    for i in range(0, len(queue), 10):  # renders with layer ids, ≤ 10 frames a call
        chunk = queue[i:i + 10]
        try:
            urls = figapi.get(f"/v1/images/{item['key']}?ids={','.join(s['id'] for s in chunk)}{SVG_Q}", token, log=log)["images"]
        except (figapi.FigmaError, RuntimeError, OSError):
            urls = {}
            for s in chunk:
                try:
                    urls.update(figapi.get(f"/v1/images/{item['key']}?ids={s['id']}{SVG_Q}", token, tries=4, log=log)["images"])
                except (figapi.FigmaError, RuntimeError, OSError) as e:
                    log(f"  no render for {s['name']} ({str(e)[:60]})")
        for s in chunk:
            doc, rec = docs.pop(s["id"])
            u = urls.get(s["id"])
            if u:
                tsvg, n = tokenize_rendered(_text(u), doc, VARS)
                write_text(lp(tok_path(ws, sc, s)), tsvg)
                rec.update(svg="ok", method="render", colors_tokenized=n)
            else:
                rec["svg"] = "none"
            U["screens"][s["id"]] = rec
        write_json(up, U)
        log(f"  rendered {min(i + 10, len(queue))}/{len(queue)}")
    sv = U["screens"].values()
    U["generated"] = now_iso()
    U["summary"] = {"screens": len(U["screens"]), "token_svgs": sum(r.get("svg") == "ok" for r in sv),
                    "raw_is_token_svg": sum(r.get("svg") == "raw" for r in sv),
                    "by_method": {m: sum(r.get("method") == m for r in sv) for m in ("hex", "render")},
                    "colors_tokenized": sum(r.get("colors_tokenized", 0) for r in sv),
                    "unresolved_variables": sum(bool((r.get("tokens") or {}).get("_unresolved")) for r in sv),
                    "screens_with_unbound_colors": sum(bool(r.get("unbound_colors")) for r in sv)}
    write_json(up, U)
    return U["summary"]
