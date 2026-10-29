"""Dev handoff: a fresh, self-contained package for the pages a developer needs, in <workspace>/handoff/<name>/.

Steps (each resumable, the backup is never touched):
  screens   fresh PNG + SVG of every frame on the chosen pages (frame numbers match the backup where they exist)
  tokens    token SVGs + token report, if variables are saved (kit.py tokens)
  code      Figma's own design-to-code per frame through Figma desktop's MCP server: code/<frame>.tsx (+ .styles.md,
            assets/). Needs Figma desktop open with its MCP server on; skipped with a note otherwise.
  anatomy   components/<frame>.html for component frames: properties, variants, spacing / radius / colour tokens, layers
  used-by   which components each frame uses (components-usage.json)
  pages     frames/<frame>.html with tabs Design · Code · Tokens · Anatomy
  gallery   index.html (the backup gallery, with a "Code & specs" link per frame) + README.md + tokens/"""
import html
import os
import re
import shutil
import time
import urllib.request
from collections import Counter, defaultdict
from urllib.parse import quote

from . import export, figapi, gallery, mcp, tokens, variables
from .names import lp, safe
from .util import now_iso, read_json, write_json, write_text

esc = html.escape
COMP = ("COMPONENT_SET", "COMPONENT", "INSTANCE")
ASSET = re.compile(r"https?://(?:localhost|127\.0\.0\.1):3845/assets/([0-9a-f]+\.[a-z0-9]+)")
SPLIT = re.compile(r"\n?SUPER CRITICAL", re.I)
SZ = re.compile(r"\s*\[(M|D)\]\s*$")


def base_dir(ws, name):
    return os.path.join(ws.root, "handoff", safe(name, 80))


def prepare(ws, item, page_ids, name, token, log=print):
    """List the frames on the chosen pages (fresh from Figma) → <base>/screens.json."""
    base = base_dir(ws, name)
    inv = read_json(os.path.join(ws.station, "inventory.json"))
    names = {p["id"]: p["name"] for p in inv["files"][item["key"]]["pages"]}
    pages = [{"id": pid, "name": names[pid], "dir": safe(names[pid])} for pid in page_ids]
    out, sections = [], []
    for p in pages:
        d = figapi.get(f"/v1/files/{item['key']}/nodes?ids={p['id']}&depth=6", token, log=log)
        export._walk((d.get("nodes", {}).get(p["id"]) or {}).get("document", {}), [], out, sections, p)
    backup = read_json(export.screens_path(ws, item["key"]), {"screens": []})
    old = {s["id"]: s["n"] for s in backup["screens"]}
    prev = read_json(os.path.join(base, "screens.json"), {"screens": []})
    old.update({s["id"]: s["n"] for s in prev["screens"] if s["id"] not in old})
    nxt = max(old.values(), default=0)
    for s in out:
        if s["id"] in old:
            s["n"] = old[s["id"]]
        else:
            nxt += 1
            s["n"] = nxt
    out.sort(key=lambda s: s["n"])
    sc = {"key": item["key"], "name": item["name"], "project": item["project"], "dir": "", "base": base,
          "pages": pages, "screens": out, "sections": sections,
          "handoff": {"name": name, "pages": [p["name"] for p in pages], "prepared": now_iso()}}
    write_json(os.path.join(base, "screens.json"), sc)
    log(f"  {len(out)} frames on {', '.join(p['name'] for p in pages)} "
        f"({sum(s['id'] not in {x['id'] for x in backup['screens']} for s in out)} not in the backup)")
    return sc


def stem(ws, sc, s):
    return os.path.splitext(os.path.basename(export.target(ws, sc, s, "png")))[0]


def code_path(ws, sc, s):
    return os.path.join(sc["base"], "code", stem(ws, sc, s) + ".tsx")


# ── code (Figma desktop MCP) ──────────────────────────────────────────────────────────────────────────────────────
def code(ws, sc, log=print, client=None):
    """Two passes: forced full code (2-min cap per frame), then the failures again without forcing (forced code can hang).
    Figma's one-off Code Connect notice → ask again. Returns (done, failed ids) or None when the MCP server isn't there."""
    todo = [s for s in sc["screens"] if not os.path.exists(lp(code_path(ws, sc, s)))]
    if not todo:
        return 0, []
    try:
        c = client or mcp.Client(timeout=120)
    except Exception as e:  # noqa: BLE001
        log(f"  code skipped: Figma desktop's MCP server isn't answering ({str(e)[:60]})")
        return None
    os.makedirs(lp(os.path.join(sc["base"], "code", "assets")), exist_ok=True)
    done, fails = 0, []
    for force, timeout, items in ((True, 120, todo), (False, 180, None)):
        items = items if items is not None else [s for s in todo if s["id"] in fails]
        if not items:
            break
        if not force:
            log(f"  second pass without forced code: {len(items)} frames")
            fails = []
        c.timeout = timeout
        for s in items:
            txt = None
            for attempt in range(2 if force else 3):
                try:
                    txt = mcp.text_of(c.tool("get_design_context", nodeId=s["id"], clientLanguages="typescript",
                                             clientFrameworks="react", excludeScreenshot=True, forceCode=force))
                    if "code connect" in txt.lower()[:400]:
                        txt = None
                        continue
                    break
                except Exception as e:  # noqa: BLE001
                    log(f"  retry {s['name'][:40]} ({str(e)[:60]})")
                    time.sleep(5 * (attempt + 1))
                    try:
                        c = client or mcp.Client(timeout=timeout)
                    except Exception:  # noqa: BLE001
                        pass
            if not txt:
                fails.append(s["id"])
                continue
            m = SPLIT.search(txt)
            src, notes = (txt[:m.start()], txt[m.start():]) if m else (txt, "")
            for a in sorted(set(ASSET.findall(src))):
                dst = os.path.join(sc["base"], "code", "assets", a)
                if not os.path.exists(lp(dst)):
                    for _ in range(3):
                        try:
                            with urllib.request.urlopen(f"http://127.0.0.1:3845/assets/{a}", timeout=60) as r, open(lp(dst), "wb") as f:
                                f.write(r.read())
                            break
                        except OSError:
                            time.sleep(3)
            src = ASSET.sub(lambda mm: "./assets/" + mm.group(1), src)
            head = (f"// {s['name']} · Figma node {s['id']} · {s['page']}" + (f" / {s['section']}" if s.get("section") else "")
                    + f"\n// Figma design-to-code reference ({now_iso()[:10]}). Not production code: adapt it to your components."
                    + "\n// Tokens appear as var(--<figma variable>, <fallback>): load tokens/tokens.css.\n\n")
            p = code_path(ws, sc, s)
            write_text(lp(p), head + src.rstrip() + "\n")
            sty = re.search(r"These styles are contained in the design:(.*?)(?:Image assets are stored|$)", notes, re.S)
            if sty:
                parts = [x.strip() for x in re.split(r"\),\s+(?=[A-Z][^:]{0,60}: (?:Font|Effect)\()", sty.group(1).strip().rstrip(".")) if x.strip()]
                write_text(lp(p[:-4] + ".styles.md"), f"# Styles in {s['name']}\n\n"
                           + "\n".join("- " + (x if x.endswith(")") else x + ")") for x in parts) + "\n")
            done += 1
            log(f"  code {done}/{len(todo)} {s['name'][:40]}")
    return done, fails


# ── anatomy ───────────────────────────────────────────────────────────────────────────────────────────────────────
PAGE_CSS = """:root{--bg:#f6f7f9;--panel:#fff;--fg:#1c1f24;--mut:#596070;--line:#dfe2e8;--head:#eceff4;--acc:#2457c9;--accbg:rgba(36,87,201,.1);--code:#f0f2f6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14161a;--panel:#1d2026;--fg:#e8eaee;--mut:#9aa3b0;--line:#2c313a;--head:#1d2026;--acc:#6e9bff;--accbg:rgba(110,155,255,.14);--code:#101215}}
:root[data-theme="dark"]{--bg:#14161a;--panel:#1d2026;--fg:#e8eaee;--mut:#9aa3b0;--line:#2c313a;--head:#1d2026;--acc:#6e9bff;--accbg:rgba(110,155,255,.14);--code:#101215}
*{box-sizing:border-box}html{background:var(--bg)}
body{margin:0;padding:32px 32px 64px;background:var(--bg);color:var(--fg);font:14px/1.55 system-ui,"Segoe UI",Tahoma,"Noto Sans Arabic",sans-serif}
main{max-width:1200px;margin:0 auto}h1{font-size:22px;margin:4px 0}a{color:var(--acc)}small,em{color:var(--mut);font-size:12.5px}p{margin:0 0 8px;color:var(--mut)}
h2{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);margin:20px 0 6px}
code{font:12.5px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
thead th{background:var(--head);font-size:13px}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;border:1px solid var(--line);vertical-align:-1px;margin-right:6px}
.img{margin:12px 0;padding:12px;border-radius:8px;text-align:center;background:repeating-conic-gradient(var(--head) 0 25%,transparent 0 50%) 0 0/16px 16px}
.img img{max-width:100%;height:auto}
ul.tree,ul.tree ul{list-style:none;margin:0;padding-left:18px;border-left:1px solid var(--line)}ul.tree{padding-left:6px;border:0}
ul.tree li{margin:4px 0}.ln{font-weight:600}.tk{font-size:12.5px;color:var(--mut)}
[role=tablist]{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:20px 0 0;flex-wrap:wrap}
[role=tab]{font:inherit;color:var(--fg);background:none;border:1px solid transparent;border-bottom:0;border-radius:8px 8px 0 0;padding:8px 16px;cursor:pointer;min-height:40px}
[role=tab][aria-selected=true]{background:var(--panel);border-color:var(--line);font-weight:600;margin-bottom:-1px}
[role=tab][aria-disabled=true]{color:var(--mut);cursor:default}
[role=tabpanel]{background:var(--panel);border:1px solid var(--line);border-top:0;border-radius:0 0 10px 10px;padding:20px}
pre{margin:0;background:var(--code);border:1px solid var(--line);border-radius:8px;padding:14px;overflow:auto;max-height:70vh;font:12.5px/1.5 ui-monospace,Consolas,monospace;tab-size:2}
.bar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin-bottom:12px}
button.cp{font:inherit;color:var(--fg);background:var(--accbg);border:1px solid var(--acc);border-radius:8px;padding:5px 12px;cursor:pointer;min-height:34px}
.pair{color:var(--fg);background:var(--accbg);border-radius:8px;padding:6px 12px;display:inline-block}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
@media (max-width:760px){body{padding:20px 14px}[role=tabpanel]{padding:14px}table.v,table.v thead,table.v tbody,table.v tr,table.v th,table.v td{display:block}table.v thead{display:none}table.v tr{border-bottom:1px solid var(--line);padding:6px 0}table.v td{border:0;padding:2px 0}table.v td[data-l]::before{content:attr(data-l) ": ";color:var(--mut)}}"""
TABS_JS = """(function(){var tabs=[].slice.call(document.querySelectorAll('[role=tab]'));
function sel(t,focus){if(t.getAttribute('aria-disabled')==='true')return;tabs.forEach(function(x){var on=x===t;x.setAttribute('aria-selected',on);x.tabIndex=on?0:-1;document.getElementById(x.getAttribute('aria-controls')).hidden=!on});if(focus)t.focus();try{history.replaceState(null,'','#'+t.id.slice(4))}catch(e){}}
tabs.forEach(function(t,i){t.addEventListener('click',function(){sel(t)});t.addEventListener('keydown',function(e){var k=e.key,j=k==='ArrowRight'?i+1:k==='ArrowLeft'?i-1:k==='Home'?0:k==='End'?tabs.length-1:-9;if(j===-9)return;e.preventDefault();sel(tabs[(j+tabs.length)%tabs.length],true)})});
var h=location.hash.slice(1),t=document.getElementById('tab-'+h);sel(t&&t.getAttribute('aria-disabled')!=='true'?t:tabs[0]);
var b=document.getElementById('copy');if(b)b.addEventListener('click',function(){var c=document.getElementById('src').textContent;function ok(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy code'},1500)}
function fb(){var a=document.createElement('textarea');a.value=c;document.body.appendChild(a);a.select();try{document.execCommand('copy')}catch(x){}a.remove();ok()}
try{navigator.clipboard.writeText(c).then(ok,fb)}catch(e){fb()}});})();"""


class Anatomy:
    def __init__(self, VARS):
        self.VARS = VARS

    def tok(self, n, prop):
        b = (n.get("boundVariables") or {}).get(prop)
        if isinstance(b, list):
            b = b[0] if b else None
        if isinstance(b, dict) and "id" not in b:  # per-corner map → first corner
            b = next((x for x in b.values() if isinstance(x, dict) and x.get("id")), None)
        r = variables.resolve(b["id"], self.VARS) if isinstance(b, dict) and b.get("id") else None
        return r["css"] if r else None

    def paint(self, n, key):
        out = []
        for p in n.get(key) or []:
            if p.get("visible") is False:
                continue
            if p.get("type") == "SOLID":
                hx = "#" + "".join(f"{round(p['color'][k] * 255):02X}" for k in "rgb")
                vid = ((p.get("boundVariables") or {}).get("color") or {}).get("id")
                r = variables.resolve(vid, self.VARS) if vid else None
                out.append(f'<span class="sw" style="background:{hx}"></span>' + (f'<code>{esc(r["css"])}</code>' if r else f"{hx} <em>unbound</em>"))
            else:
                out.append(p.get("type", "").lower().replace("_", " "))
        return " ".join(out)

    def val(self, n, prop):
        v, t = n.get(prop), self.tok(n, prop)
        if v in (None, 0) and not t:
            return ""
        num = f"{v:g}px" if isinstance(v, (int, float)) else ""
        return f"<code>{esc(t)}</code>" + (f" <small>{num}</small>" if num else "") if t else (num or esc(str(v)))

    @staticmethod
    def layout(n):
        lm = n.get("layoutMode")
        if not lm or lm == "NONE":
            return "—"
        d = {"HORIZONTAL": "row →", "VERTICAL": "column ↓", "GRID": "grid"}.get(lm, lm.lower())
        al = [a.lower() for a in (n.get("primaryAxisAlignItems", ""), n.get("counterAxisAlignItems", "")) if a]
        return f"{d} <small>{esc(' / '.join(al))}</small>"

    def padding(self, n):
        ks = ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft")
        vs = [self.val(n, k) for k in ks]
        if not any(vs):
            return "—"
        return " · ".join(f"{k[7:].lower()[0]} {v or 0}" for k, v in zip(ks, vs)) if len(set(vs)) > 1 else vs[0]

    def radius(self, n):
        for k in ("cornerRadius", "topLeftRadius", "rectangleCornerRadii"):
            t = self.tok(n, k)
            if t:
                v = n.get("cornerRadius")
                return f"<code>{esc(t)}</code>" + (f" <small>{v:g}px</small>" if isinstance(v, (int, float)) else "")
        return self.val(n, "cornerRadius") or "—"

    def text_styles(self, n, styles, acc):
        if n.get("type") == "TEXT":
            sid = (n.get("styles") or {}).get("text")
            st = n.get("style", {})
            acc.add(styles.get(sid, {}).get("name", "") or f"{st.get('fontFamily', '')} {st.get('fontSize', '')}".strip())
        for c in n.get("children") or []:
            self.text_styles(c, styles, acc)
        return acc

    def tree(self, n, styles, depth=0, maxd=5):
        if n.get("visible") is False or depth > maxd:
            return ""
        bits = []
        for k, lab in (("itemSpacing", "gap"), ("paddingLeft", "pad-x"), ("paddingTop", "pad-y"), ("cornerRadius", "radius"),
                       ("rectangleCornerRadii", "radius"), ("width", "w"), ("height", "h"), ("strokeWeight", "stroke-w")):
            t = self.tok(n, k)
            if t:
                bits.append(f"{lab} <code>{esc(t)}</code>")
        for key, lab in (("fills", "fill"), ("strokes", "stroke")):
            p = self.paint(n, key)
            if p and ("<code>" in p or "unbound" in p):
                bits.append(f"{lab} {p}")
        sid = (n.get("styles") or {}).get("text")
        if sid and sid in styles:
            bits.append(f'text <code>{esc(styles[sid]["name"])}</code>')
        bb = n.get("absoluteBoundingBox") or {}
        size = f'{bb.get("width", 0):g}×{bb.get("height", 0):g}' if bb else ""
        row = (f'<li><span class="ln">{esc(n.get("name", ""))}</span> <small>{n.get("type", "").lower().replace("_", " ")} · {size}</small>'
               + (f'<div class="tk">{" · ".join(bits)}</div>' if bits else ""))
        kids = "".join(self.tree(c, styles, depth + 1, maxd) for c in n.get("children") or [])
        return row + (f"<ul>{kids}</ul>" if kids else "") + "</li>"

    def page(self, ws, sc, s, n, styles, comps, code_rel):
        png = export.target(ws, sc, s, "png")
        rel = lambda p: "../" + "/".join(quote(x, safe="") for x in os.path.relpath(p, sc["base"]).replace(os.sep, "/").split("/"))  # noqa: E731
        props = n.get("componentPropertyDefinitions") or {}
        cname = lambda v: (comps or {}).get(str(v), {}).get("name") or str(v)  # noqa: E731
        prow = "".join(
            f'<tr><td data-l="Property"><code>{esc(k.split("#")[0])}</code></td><td data-l="Type">{esc(v.get("type", "").lower().replace("_", " "))}</td>'
            f'<td data-l="Options">{esc(" · ".join(v.get("variantOptions") or []) or "—")}</td>'
            f'<td data-l="Default"><code>{esc(cname(v.get("defaultValue", "")) if v.get("type") == "INSTANCE_SWAP" else str(v.get("defaultValue", "")))}</code></td></tr>'
            for k, v in props.items())
        if not prow and n.get("componentProperties"):
            prow = "".join(f'<tr><td data-l="Property"><code>{esc(k.split("#")[0])}</code></td><td data-l="Type">{esc(v.get("type", "").lower())}</td>'
                           f'<td data-l="Options">—</td><td data-l="Value"><code>{esc(str(v.get("value", "")))}</code></td></tr>'
                           for k, v in n["componentProperties"].items())
        variants = [c for c in n.get("children") or [] if c.get("type") == "COMPONENT"] if n.get("type") == "COMPONENT_SET" else [n]
        vrow = ""
        for v in variants:
            bb = v.get("absoluteBoundingBox") or {}
            ts = sorted(x for x in self.text_styles(v, styles, set()) if x.strip())
            vrow += (f'<tr><td data-l="Variant">{esc(v.get("name", ""))}</td><td data-l="Size">{bb.get("width", 0):g}×{bb.get("height", 0):g}</td>'
                     f'<td data-l="Layout">{self.layout(v)}</td><td data-l="Gap">{self.val(v, "itemSpacing") or "—"}</td>'
                     f'<td data-l="Padding">{self.padding(v)}</td><td data-l="Radius">{self.radius(v)}</td>'
                     f'<td data-l="Fill">{self.paint(v, "fills") or "—"}</td><td data-l="Stroke">{self.paint(v, "strokes") or "—"}'
                     + (f' {self.val(v, "strokeWeight")}' if v.get("strokes") else "") + f'</td><td data-l="Text">{esc(" · ".join(ts)) or "—"}</td></tr>')
        default = variants[0] if variants else n
        fig = f"https://www.figma.com/design/{sc['key']}?node-id={s['id'].replace(':', '-')}"
        title = s["name"] if len(s["name"]) <= 58 else s["name"][:57].rstrip() + "…"
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}: anatomy</title><style>{PAGE_CSS}</style></head>
<body><main>
<p><a href="../index.html">← Handoff gallery</a></p>
<h1 dir="auto">{esc(s['name'])}</h1>
<p>{esc(n.get('type', '').lower().replace('_', ' '))} · {len(variants)} variant{'s' if len(variants) != 1 else ''} · node {esc(s['id'])} · <a href="{fig}">Open in Figma</a>{' · <a href="' + code_rel + '">Code (.tsx)</a>' if code_rel else ''}</p>
{('<p>' + esc(n.get('description', '')) + '</p>') if n.get('description') else ''}
<div class="img"><img src="{rel(png)}" alt="{esc(s['name'])}, all variants"></div>
<h2>Properties</h2>
{('<table class="v"><thead><tr><th scope="col">Property</th><th scope="col">Type</th><th scope="col">Options</th><th scope="col">Default</th></tr></thead><tbody>' + prow + '</tbody></table>') if prow else '<p>No component properties.</p>'}
<h2>Variants</h2>
<table class="v"><thead><tr><th scope="col">Variant</th><th scope="col">Size</th><th scope="col">Layout</th><th scope="col">Gap</th><th scope="col">Padding</th><th scope="col">Radius</th><th scope="col">Fill</th><th scope="col">Stroke</th><th scope="col">Text styles</th></tr></thead><tbody>{vrow}</tbody></table>
<h2>Layers <small>(default variant: {esc(default.get('name', ''))})</small></h2>
<ul class="tree">{self.tree(default, styles)}</ul>
<!--usedby--><!--/usedby-->
<p style="margin-top:24px"><small>From Figma's layer data by figma-offline-kit. Token names are the CSS custom properties in tokens/tokens.css; "unbound" = a colour hard-coded in Figma.</small></p>
</main></body></html>
"""


def anatomy(ws, sc, VARS, token, log=print):
    A = Anatomy(VARS)
    items = [s for s in sc["screens"] if s["type"] in COMP]
    os.makedirs(lp(os.path.join(sc["base"], "components")), exist_ok=True)
    n = 0
    for k in range(0, len(items), 10):
        chunk = items[k:k + 10]
        r = figapi.get(f"/v1/files/{sc['key']}/nodes?ids={','.join(s['id'] for s in chunk)}", token, log=log).get("nodes", {})
        for s in chunk:
            nd = r.get(s["id"])
            if not nd:
                continue
            cp = code_path(ws, sc, s)
            code_rel = "../code/" + quote(os.path.basename(cp)) if os.path.exists(lp(cp)) else ""
            write_text(lp(os.path.join(sc["base"], "components", stem(ws, sc, s) + ".html")),
                       A.page(ws, sc, s, nd["document"], nd.get("styles") or {}, nd.get("components") or {}, code_rel))
            n += 1
    log(f"  anatomy: {n} component pages")
    return n


def used_by(ws, sc, token, log=print):
    """Instances on each frame → the handoff's component frames (by id, else by name: dev pages hold copies)."""
    comp_ids = {s["id"] for s in sc["screens"] if s["type"] in ("COMPONENT_SET", "COMPONENT")}
    comp_by_name = {s["name"]: s["id"] for s in sc["screens"] if s["type"] in ("COMPONENT_SET", "COMPONENT")}
    frames = [s for s in sc["screens"] if s["type"] not in ("COMPONENT_SET", "COMPONENT")]
    U = {"frames": {}}
    for k in range(0, len(frames), 8):
        chunk = frames[k:k + 8]
        r = figapi.get(f"/v1/files/{sc['key']}/nodes?ids={','.join(s['id'] for s in chunk)}", token, log=log).get("nodes", {})
        for s in chunk:
            nd = r.get(s["id"])
            if not nd:
                continue
            comps, sets, used = nd.get("components") or {}, nd.get("componentSets") or {}, Counter()

            def walk(n):
                if n.get("visible") is False:
                    return
                if n.get("type") == "INSTANCE":
                    cid = n.get("componentId")
                    meta = comps.get(cid) or {}
                    sid = meta.get("componentSetId")
                    tgt = (sid if sid in comp_ids else cid if cid in comp_ids
                           else comp_by_name.get((sets.get(sid) or {}).get("name")) or comp_by_name.get(meta.get("name")))
                    if tgt and tgt != s["id"]:
                        used[tgt] += 1
                for c in n.get("children") or []:
                    walk(c)
            walk(nd["document"])
            U["frames"][s["id"]] = [[c, n] for c, n in used.most_common()]
    rev = defaultdict(list)
    for fid, lst in U["frames"].items():
        for c, _ in lst:
            rev[c].append(fid)
    U["components"] = dict(rev)
    write_json(os.path.join(sc["base"], "components-usage.json"), U)
    log(f"  used-by: {len(rev)} components used in {sum(bool(v) for v in U['frames'].values())} frames")
    return U


KL = {"color": "Colour", "spacing": "Spacing", "radius": "Radius", "size": "Size", "stroke": "Stroke width", "type": "Type variable",
      "effect": "Effect", "opacity": "Opacity", "text-style": "Text style", "effect-style": "Effect style", "color-style": "Colour style"}


def frame_pages(ws, sc, log=print):
    base = sc["base"]
    U = (read_json(tokens.usage_path(ws, sc)) or {}).get("screens", {})
    CU = read_json(os.path.join(base, "components-usage.json"), {"frames": {}, "components": {}})
    by_id = {s["id"]: s for s in sc["screens"]}
    stems = {s["id"]: stem(ws, sc, s) for s in sc["screens"]}
    groups = defaultdict(lambda: {"M": [], "D": []})  # responsive pairs: "<name> [M]" ⇄ "<name> [D]" in one section
    for s in sc["screens"]:
        m = SZ.search(s["name"])
        if m:
            groups[(s.get("section") or "", SZ.sub("", s["name"]).strip().lower())][m.group(1)].append(s["id"])
    other = {}
    for g in groups.values():
        if g["M"] and g["D"]:
            for x in g["M"]:
                other[x] = ("Desktop", g["D"])
            for x in g["D"]:
                other[x] = ("Mobile", g["M"])
    os.makedirs(lp(os.path.join(base, "frames")), exist_ok=True)
    rel = lambda p: "../" + "/".join(quote(x, safe="") for x in os.path.relpath(p, base).replace(os.sep, "/").split("/"))  # noqa: E731
    for s in sc["screens"]:
        st = stems[s["id"]]
        png, svg, tsvg, cp = (export.target(ws, sc, s, "png"), export.target(ws, sc, s, "svg"),
                              tokens.tok_path(ws, sc, s), code_path(ws, sc, s))
        comp = os.path.join(base, "components", st + ".html")
        links = " · ".join(f'<a href="{rel(p)}">{lab}</a>' for p, lab in ((png, "PNG"), (svg, "SVG"), (tsvg, "Token SVG")) if os.path.exists(lp(p)))
        fig = f"https://www.figma.com/design/{sc['key']}?node-id={s['id'].replace(':', '-')}"
        design = (f'<div class="bar"><span>{links}</span><a href="{fig}">Open in Figma</a></div>'
                  + (f'<div class="img"><img src="{rel(png)}" alt="{esc(s["name"])}" loading="lazy"></div>' if os.path.exists(lp(png)) else "<p>No render.</p>"))
        code_html = ""
        if os.path.exists(lp(cp)):
            with open(lp(cp), encoding="utf-8") as f:
                src = f.read()
            sty = cp[:-4] + ".styles.md"
            code_html = (f'<div class="bar"><button type="button" class="cp" id="copy">Copy code</button><a href="{rel(cp)}">.tsx file</a>'
                         + (f' · <a href="{rel(sty)}">styles</a>' if os.path.exists(lp(sty)) else "")
                         + ' · <small>React + Tailwind reference from Figma. Load <code>tokens/tokens.css</code>; assets in <code>code/assets/</code>.</small></div>'
                         + f'<pre tabindex="0" aria-label="Code, scrollable"><code id="src">{esc(src)}</code></pre>')
        r = U.get(s["id"])
        tok_html = ""
        if r:
            parts = []
            for k, lst in (r.get("tokens") or {}).items():
                if k.startswith("_"):
                    continue
                rows = "".join('<tr><td>' + (f'<span class="sw" style="background:{esc(t["value"])}"></span>' if t.get("value") else "")
                               + f'<code>{esc(t.get("css") or ("." + t["class"] if t.get("class") else ""))}</code></td><td>{esc(t["figma"])}</td><td>×{t["count"]}</td></tr>'
                               for t in lst)
                parts.append(f'<h2>{KL.get(k, k)} · {len(lst)}</h2><table><tbody>{rows}</tbody></table>')
            ub = r.get("unbound_colors") or []
            if ub:
                parts.append(f'<h2>Unbound colours · {len(ub)}</h2><p>Hard-coded in Figma (no variable, no style).</p><table><tbody>'
                             + "".join(f'<tr><td><span class="sw" style="background:{u["hex"]}"></span><code>{u["hex"]}</code></td>'
                                       f'<td>{esc(", ".join(u.get("layers") or []))}</td><td>×{u["count"]}</td></tr>' for u in ub) + "</tbody></table>")
            tok_html = "".join(parts) or "<p>No tokens bound on this frame.</p>"
        anat = (f'<p>Variants, properties, spacing / radius / colour tokens and the layer tree of this component.</p>'
                f'<p><a href="{rel(comp)}">Open the anatomy page →</a></p>' if os.path.exists(lp(comp)) else "")
        used = [u for u in CU["frames"].get(s["id"]) or [] if u[0] in by_id]
        if used:
            rows = ""
            for cid, cnt in used:
                cpage = os.path.join(base, "components", stems[cid] + ".html")
                name = f'<a href="{rel(cpage)}">{esc(by_id[cid]["name"])}</a>' if os.path.exists(lp(cpage)) else esc(by_id[cid]["name"])
                rows += f'<tr><td>{name}</td><td>×{cnt}</td><td><a href="{quote(stems[cid])}.html#code">code</a></td></tr>'
            anat += f'<h2>Components used · {len(used)}</h2><table><tbody>{rows}</tbody></table>'
        users = [u for u in CU["components"].get(s["id"]) or [] if u in by_id]
        if users:
            anat += (f'<h2>Used in · {len(users)} frame{"s" if len(users) != 1 else ""}</h2><table><tbody>'
                     + "".join(f'<tr><td><a href="{quote(stems[u])}.html">{esc(by_id[u]["name"])}</a></td><td><small>{esc(by_id[u].get("section") or "")}</small></td></tr>'
                               for u in users) + "</tbody></table>")
            if os.path.exists(lp(comp)):
                with open(lp(comp), encoding="utf-8") as f:
                    h = f.read()
                blk = ("<!--usedby--><h2>Used in <small>(" + str(len(users)) + " frames)</small></h2><ul>"
                       + "".join(f'<li><a href="../frames/{quote(stems[u])}.html">{esc(by_id[u]["name"])}</a></li>' for u in users)
                       + "</ul><!--/usedby-->")
                h = h[:h.index("<!--usedby-->")] + blk + h[h.index("<!--/usedby-->") + len("<!--/usedby-->"):]
                write_text(lp(comp), h)
        pair = ""
        if s["id"] in other:
            lab, ids = other[s["id"]]
            pair = (f'<p class="pair">⇄ Responsive pair, <b>{lab}</b>: ' + " · ".join(f'<a href="{quote(stems[x])}.html">{esc(by_id[x]["name"])}</a>' for x in ids)
                    + ". The same screen in the other size: build it once, responsive.</p>")
        tabs = [("design", "Design", design), ("code", "Code", code_html), ("tokens", "Tokens", tok_html), ("anatomy", "Anatomy", anat)]
        tl = "".join(f'<button type="button" role="tab" id="tab-{k}" aria-controls="p-{k}" aria-selected="false" tabindex="-1"'
                     + (' aria-disabled="true" title="Not available for this frame"' if not body else "") + f'>{lab}</button>' for k, lab, body in tabs)
        tp = "".join(f'<div role="tabpanel" id="p-{k}" aria-labelledby="tab-{k}" tabindex="0" hidden>{body or "<p>Not available for this frame.</p>"}</div>'
                     for k, lab, body in tabs)
        title = s["name"] if len(s["name"]) <= 58 else s["name"][:57].rstrip() + "…"
        write_text(lp(os.path.join(base, "frames", st + ".html")), f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}: handoff</title><style>{PAGE_CSS}</style></head>
<body><main>
<p><a href="../index.html">← Handoff gallery</a></p>
<h1 dir="auto">{esc(s['name'])}</h1>
<p>{esc(s['page'])}{(' / ' + esc(s['section'])) if s.get('section') else ''} · {s.get('w', 0)}×{s.get('h', 0)} · {esc(s['type'].lower().replace('_', ' '))} · node {esc(s['id'])}</p>
{pair}
<div role="tablist" aria-label="Frame details">{tl}</div>
{tp}
</main><script>{TABS_JS}</script></body></html>
""")
    log(f"  frame pages: {len(sc['screens'])}")


def readme(ws, sc, res):
    lines = [f"# Dev handoff: {sc['name']}", "",
             f"Pages: {', '.join(sc['handoff']['pages'])} · {len(sc['screens'])} frames · made {now_iso()[:16].replace('T', ' ')} by figma-offline-kit.",
             "Fresh from Figma when it was made; the backup is a separate snapshot.", "",
             "| Path | What |", "|---|---|",
             "| `index.html` | gallery of every frame; **Code & specs** opens the frame page |",
             "| `frames/<frame>.html` | per frame: Design · Code · Tokens · Anatomy |",
             "| `screens/png · svg · svg-tokens/` | images; token SVGs have colours as `var(--token, #hex)` |",
             "| `code/<frame>.tsx` | Figma's design-to-code reference (React + Tailwind), assets in `code/assets/` |",
             "| `components/<frame>.html` | anatomy of component frames: properties, variants, tokens, layers |",
             "| `tokens/` | the design system's `tokens.css` / `_tokens.scss` (load `tokens.css` to run the code on your tokens) |",
             "| `tokens-usage.json` · `components-usage.json` · `screens.json` | the data behind the pages |", "",
             "## State", ""] + [f"- {k}: {v}" for k, v in res.items()]
    write_text(lp(os.path.join(sc["base"], "README.md")), "\n".join(lines) + "\n")


def run(ws, item, page_ids, name, token, log=print, mcp_client=None):
    sc = prepare(ws, item, page_ids, name, token, log)
    res = {}
    export.export(ws, sc, token, ["png", "svg"], log=log)
    res["screens"] = f"{len(sc['screens'])} frames, PNG + SVG"
    queue = read_json(os.path.join(ws.station, "plan.json"))["queue"]
    VARS = variables.load_all(ws, queue)
    if VARS:
        s = tokens.run_file(ws, item, VARS, token, log=log, sc=sc)
        res["tokens"] = f"{s['token_svgs']} token SVGs, {s['screens_with_unbound_colors']} frames with unbound colours"
        tdir = os.path.join(sc["base"], "tokens")
        for q in queue:
            vd = variables.var_dir(ws, q)
            for fn in ("tokens.css", "_tokens.scss"):
                if os.path.exists(lp(os.path.join(vd, fn))):
                    os.makedirs(lp(tdir), exist_ok=True)
                    dst = fn if len([x for x in queue if os.path.exists(lp(os.path.join(variables.var_dir(ws, x), fn)))]) == 1 \
                        else f"{safe(q['name'])}.{fn}"
                    shutil.copy2(lp(os.path.join(vd, fn)), lp(os.path.join(tdir, dst)))
    else:
        res["tokens"] = "skipped: no variables saved (python kit.py tokens vars / import)"
    c = code(ws, sc, log=log, client=mcp_client)
    res["code"] = ("skipped: open Figma desktop on this file, turn on its MCP server, then run handoff again" if c is None
                   else f"{len([s for s in sc['screens'] if os.path.exists(lp(code_path(ws, sc, s)))])} / {len(sc['screens'])} frames"
                   + (f", {len(c[1])} failed (run again to retry)" if c[1] else ""))
    na = anatomy(ws, sc, VARS, token, log)
    res["anatomy"] = f"{na} component page{'s' if na != 1 else ''}"
    used_by(ws, sc, token, log)
    frame_pages(ws, sc, log)
    gallery.build(ws, sc)
    readme(ws, sc, res)
    write_json(os.path.join(sc["base"], "handoff.json"), dict(sc["handoff"], finished=now_iso(), result=res))
    return sc["base"], res
