"""Design-system variables: get them, keep them, write them as CSS / SCSS.

Sources, best first:
  rest    GET /v1/files/<key>/variables/local (Figma Enterprise plans only)
  mcp     the AI runs templates/variables.js through Figma's MCP (`use_figma`) and saves the JSON it returns
  native  Figma's own export (Variables panel → right-click a collection → Export modes): a zip of <Mode>.tokens.json
Everything ends up in backup/<project>/<file>/variables/:
  variables.figma.json   REST shape {meta: {variables, variableCollections}} (rest and mcp)
  figma-native/          the native export as saved (native)
  tokens.css · _tokens.scss   CSS custom properties per collection (default mode on :root, other modes on
                         [data-<collection>="<mode>"]); names = the variable's Web code syntax if set, else its slugged path."""
import json
import os
import re
import shutil
import zipfile

from . import figapi
from .names import lp
from .util import REPO, now_iso, read_json, write_json, write_text

UNITLESS = re.compile(r"weight|opacity|z-?index|ratio|scale|line-?height-?multiplier", re.I)
UNITLESS_SCOPES = {"FONT_WEIGHT", "OPACITY"}
SCRIPT = os.path.join(REPO, "templates", "variables.js")


def var_dir(ws, q):
    return os.path.join(ws.backup, q["dir"], "variables")


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-") or "x"


def from_rest(ws, q, token, log=print):
    """Try the REST endpoint. Returns the dump, or None when the plan doesn't allow it (403/404)."""
    try:
        d = figapi.get(f"/v1/files/{q['key']}/variables/local", token, tries=3, log=log)
    except figapi.FigmaError as e:
        if e.status in (400, 403, 404):
            return None
        raise
    return save(ws, q, d, "rest")


def save(ws, q, d, source):
    meta = d.get("meta") or d
    if not meta.get("variables"):
        return None
    out = {"meta": {"variables": meta["variables"], "variableCollections": meta["variableCollections"]},
           "x-backup": {"fileKey": q["key"], "file": q["name"], "source": source, "saved": now_iso()}}
    write_json(os.path.join(var_dir(ws, q), "variables.figma.json"), out)
    write_css(ws, q, out)
    return out


def import_path(ws, q, path):
    """An MCP JSON dump, or a native export (zip or folder of .tokens.json)."""
    if path.lower().endswith(".json") and not path.lower().endswith(".tokens.json"):
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        if isinstance(d, str):  # some MCP clients return the JSON as a string
            d = json.loads(d)
        res = save(ws, q, d, "mcp")
        if not res:
            raise ValueError(f"{path}: no variables found (expected {{meta: {{variables, variableCollections}}}})")
        return "mcp", len(res["meta"]["variables"])
    dst = os.path.join(var_dir(ws, q), "figma-native")
    os.makedirs(lp(dst), exist_ok=True)
    n = 0
    if zipfile.is_zipfile(path):
        sub = os.path.join(dst, os.path.splitext(os.path.basename(path))[0])
        with zipfile.ZipFile(path) as z:
            for m in z.namelist():
                if m.endswith(".json") and ".." not in m and not os.path.isabs(m):
                    os.makedirs(lp(sub), exist_ok=True)
                    with z.open(m) as src, open(lp(os.path.join(sub, os.path.basename(m))), "wb") as out:
                        shutil.copyfileobj(src, out)
                    n += 1
    elif os.path.isdir(path):
        for fn in os.listdir(path):
            if fn.endswith(".json"):
                shutil.copy2(os.path.join(path, fn), lp(os.path.join(dst, fn)))
                n += 1
    elif path.endswith(".json"):
        shutil.copy2(path, lp(os.path.join(dst, os.path.basename(path))))
        n = 1
    if not n:
        raise ValueError(f"{path}: no .tokens.json files found")
    return "native", n


def status(ws, q):
    d = var_dir(ws, q)
    dump = read_json(os.path.join(d, "variables.figma.json"))
    native = os.path.isdir(lp(os.path.join(d, "figma-native")))
    return {"source": dump["x-backup"]["source"] if dump else ("native" if native else None),
            "variables": len(dump["meta"]["variables"]) if dump else 0, "native": native}


# ── CSS / SCSS ────────────────────────────────────────────────────────────────────────────────────────────────────
def css_names(V, cols):
    """{variable id: '--name'}: Web code syntax if the designer set one, else the slugged path (collection-prefixed on clashes)."""
    out, used = {}, {}
    for vid, v in V.items():
        web = (v.get("codeSyntax") or {}).get("WEB", "")
        m = re.search(r"--[\w-]+", web)
        name = m.group(0) if m else "--" + slug(v["name"].replace("/", "-"))
        if name in used and used[name] != vid:
            name = "--" + slug(cols.get(v["variableCollectionId"], {}).get("name", "")) + "-" + name[2:]
        used[name] = vid
        out[vid] = name
    return out


def _color(c):
    r, g, b, a = (round(c.get(k, 1 if k == "a" else 0) * 255) for k in "rgba")
    return f"#{r:02x}{g:02x}{b:02x}" if a == 255 else f"rgba({r}, {g}, {b}, {round(a / 255, 3)})"


def _value(v, x, names):
    if isinstance(x, dict) and x.get("type") == "VARIABLE_ALIAS":
        return f"var({names[x['id']]})" if x["id"] in names else None
    t = v["resolvedType"]
    if t == "COLOR" and isinstance(x, dict):
        return _color(x)
    if t == "FLOAT":
        n = int(x) if float(x).is_integer() else round(x, 4)
        unitless = UNITLESS.search(v["name"]) or (v.get("scopes") and set(v["scopes"]) <= UNITLESS_SCOPES)
        return f"{n}" if unitless or n == 0 else f"{n}px"
    if t == "STRING":
        return json.dumps(x, ensure_ascii=False)
    return None  # booleans have no CSS meaning


def write_css(ws, q, dump):
    V, cols = dump["meta"]["variables"], dump["meta"]["variableCollections"]
    names = css_names(V, cols)
    css = [f"/* Design tokens from Figma: {q['name']}. Generated by figma-offline-kit {now_iso()[:10]}. */", ""]
    scss = [f"// Design tokens from Figma: {q['name']}. Each SCSS variable points at the CSS custom property in tokens.css.", ""]
    for cid, c in cols.items():
        vids = [x for x in c.get("variableIds", []) if x in V]
        modes = c.get("modes", [])
        default = c.get("defaultModeId") or (modes[0]["modeId"] if modes else None)
        for m in sorted(modes, key=lambda m: m["modeId"] != default):
            sel = ":root" if m["modeId"] == default else f'[data-{slug(c["name"])}="{slug(m["name"])}"]'
            lines = []
            for vid in vids:
                v = V[vid]
                val = _value(v, v.get("valuesByMode", {}).get(m["modeId"]), names)
                if val is not None:
                    lines.append(f"  {names[vid]}: {val};")
            if lines:
                css += [f"/* {c['name']} · {m['name']} */", sel + " {", *lines, "}", ""]
        scss += [f"// {c['name']}"] + [f"${names[v][2:]}: var({names[v]});" for v in vids if V[v]["resolvedType"] != "BOOLEAN"] + [""]
    write_text(os.path.join(var_dir(ws, q), "tokens.css"), "\n".join(css))
    write_text(os.path.join(var_dir(ws, q), "_tokens.scss"), "\n".join(scss))


# ── lookup for screens ────────────────────────────────────────────────────────────────────────────────────────────
def load_all(ws, queue):
    """{variable id or 'key:<key>': {name, css, type, collection, ds, hex}} across every saved dump in the workspace.
    Library variables used in other files appear as 'VariableID:<key>/<id>', hence the key index."""
    out = {}
    for q in queue:
        dump = read_json(os.path.join(var_dir(ws, q), "variables.figma.json"))
        if not dump:
            continue
        V, cols = dump["meta"]["variables"], dump["meta"]["variableCollections"]
        names = css_names(V, cols)

        def hexval(v, depth=0):
            c = cols.get(v["variableCollectionId"], {})
            val = (v.get("valuesByMode") or {}).get(c.get("defaultModeId"))
            if val is None and v.get("valuesByMode"):
                val = next(iter(v["valuesByMode"].values()))
            if isinstance(val, dict) and val.get("type") == "VARIABLE_ALIAS":
                t = V.get(val["id"])
                return hexval(t, depth + 1) if t and depth < 10 else None
            if isinstance(val, dict) and "r" in val:
                h = "#" + "".join(f"{round(val[k] * 255):02X}" for k in "rgb")
                return h + (f"{round(val.get('a', 1) * 255):02X}" if val.get("a", 1) < 1 else "")
            return None
        for vid, v in V.items():
            rec = {"name": v["name"], "css": names[vid], "type": v["resolvedType"], "ds": q["name"],
                   "collection": cols.get(v["variableCollectionId"], {}).get("name", ""),
                   "hex": hexval(v) if v["resolvedType"] == "COLOR" else None}
            out[vid] = rec
            if v.get("key"):
                out["key:" + v["key"]] = rec
    return out


def resolve(vid, VARS):
    if vid in VARS:
        return VARS[vid]
    m = re.match(r"VariableID:([^/]+)/", vid or "")
    return VARS.get("key:" + m.group(1)) if m else None
