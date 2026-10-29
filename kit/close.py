"""Close: verify the backup, check drift, build the coverage page, pack the archives. Plus refresh for changed files.

- verify: every planned screen is on disk in each chosen format (PDF counts for SVG), every file has its gallery,
  every local copy is a real Figma file.
- drift: compares each file's Figma lastModified with the state its backup reflects (a per-screen SVG diff can't:
  layer ids add wrapper <g>s).
- coverage: backup/COVERAGE.html, what the backup holds per project → file → page.
- archives: one archive per project folder, tested after packing; skipped when already newer than its contents."""
import datetime
import html
import os
import shutil
import subprocess
import zipfile
from collections import Counter
from urllib.parse import quote

from . import copies, figapi
from .doctor import find_tool
from .export import screens_path, target
from .names import divider_label, lp
from .util import now_iso, read_json, write_json, write_text

STORE = {".png", ".jpg", ".fig", ".jam", ".deck", ".make", ".zip", ".pdf"}  # already compressed


def _plan(ws):
    return read_json(os.path.join(ws.station, "plan.json"), {"queue": []})


def verify(ws):
    cfg, st = ws.config(), ws.state().get("files", {})
    rows, problems, tot = [], [], Counter()
    for q in _plan(ws)["queue"]:
        if not q["pages"]:
            continue
        sc = read_json(screens_path(ws, q["key"]))
        if not sc:
            problems.append(f"{q['name']}: not exported yet")
            continue
        c = Counter()
        for s in sc["screens"]:
            c["screens"] += 1
            for ext in cfg["formats"]:
                if os.path.exists(lp(target(ws, sc, s, ext))):
                    c[ext] += 1
                elif ext == "svg" and os.path.exists(lp(target(ws, sc, s, "pdf"))):
                    c["pdf"] += 1
                elif ext == "svg" and s["id"] in st.get(q["key"], {}).get("empty_ids", []):
                    c["empty"] += 1
                else:
                    c[f"missing {ext}"] += 1
        tot.update(c)
        tot["files"] += 1
        miss = {k: v for k, v in c.items() if k.startswith("missing")}
        if miss:
            problems.append(f"{q['name']}: " + ", ".join(f"{v} {k}" for k, v in miss.items()))
        if not os.path.exists(lp(os.path.join(ws.backup, q["dir"], "index.html"))):
            problems.append(f"{q['name']}: gallery missing")
        rows.append((q, c))
    cp = read_json(copies.path(ws), {"items": {}})["items"] if cfg["local_copies"] != "skip" else {}
    for r in cp.values():
        tot[f"copy {r['status']}"] += 1
        if r["status"] == "done" and not copies.valid(r["target"]):
            problems.append(f"{r['name']}: local copy is missing or damaged")
    return {"checked": now_iso(), "totals": dict(tot), "problems": problems,
            "files": {q["key"]: dict(c) for q, c in rows}}


def drift(ws, token, log=print):
    """Which backed-up files changed in Figma after their backup? → workstation/drift.json"""
    st = ws.state().get("files", {})
    cp = read_json(copies.path(ws), {"items": {}})["items"]
    out = {"checked": now_iso(), "files": {}}
    for q in _plan(ws)["queue"]:
        exported = st.get(q["key"], {}).get("status") == "done"
        copied = cp.get(q["key"], {}).get("status") == "done"
        if not exported and not copied:
            continue
        now = figapi.get(f"/v1/files/{q['key']}?depth=1", token, log=log).get("lastModified")
        ref = st.get(q["key"], {}).get("last_modified") if exported else None
        saved = cp.get(q["key"], {}).get("done") if copied else None
        out["files"][q["key"]] = {
            "name": q["name"], "figma_now": now, "backup_state": ref, "copy_saved": saved,
            "edited_after": bool(now and ref and now > ref) or bool(now and saved and _utc(saved) < now)}
    write_json(os.path.join(ws.station, "drift.json"), out)
    return out


def _utc(local_iso):
    """'2026-10-29T15:37:21+0330' → '2026-10-29T12:07:21Z' (comparable with Figma's lastModified)."""
    try:
        return datetime.datetime.strptime(local_iso, "%Y-%m-%dT%H:%M:%S%z").astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return local_iso


def refresh(ws):
    """Move changed files' backup folders to temp/replaced/<time>/ and queue them again. Returns the names."""
    d = read_json(os.path.join(ws.station, "drift.json"), {"files": {}})
    changed = [k for k, v in d["files"].items() if v["edited_after"]]
    if not changed:
        return []
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    plan = _plan(ws)
    q = {x["key"]: x for x in plan["queue"]}
    st = ws.state()
    cp = read_json(copies.path(ws), {"items": {}})
    names = []
    for k in changed:
        src = os.path.join(ws.backup, q[k]["dir"])
        if os.path.isdir(lp(src)):
            dst = os.path.join(ws.temp, "replaced", stamp, q[k]["dir"])
            os.makedirs(lp(os.path.dirname(dst)), exist_ok=True)
            shutil.move(lp(src), lp(dst))
        st.get("files", {}).pop(k, None)
        if k in cp["items"]:
            cp["items"][k].update(status="todo", done=None, size=None, note="changed in Figma: save again")
        q[k]["last_modified"] = d["files"][k]["figma_now"]  # the re-export will reflect this state
        names.append(q[k]["name"])
    write_json(os.path.join(ws.station, "plan.json"), plan)
    write_json(ws.state_path, st)
    write_json(copies.path(ws), cp)
    return names


# ── archives ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _newest(folder):
    return max((os.path.getmtime(os.path.join(dp, f)) for dp, _, fs in os.walk(lp(folder)) for f in fs), default=0)


def archive_one(folder, out, fmt):
    tmp = out + ".partial"
    if os.path.exists(tmp):
        os.remove(tmp)
    if fmt == "zip":
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for dp, _, fs in os.walk(lp(folder)):
                for f in sorted(fs):
                    p = os.path.join(dp, f)
                    arc = os.path.relpath(p, os.path.dirname(lp(folder)))
                    z.write(p, arc, zipfile.ZIP_STORED if os.path.splitext(f)[1].lower() in STORE else zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(tmp) as z:
            bad = z.testzip()
        if bad:
            raise RuntimeError(f"archive test failed at {bad}")
    else:
        exe = find_tool(["7z", "7zz", "7za"], [os.path.join("7-Zip", "7z.exe")]) if fmt == "7z" else \
            find_tool(["rar"], [os.path.join("WinRAR", "Rar.exe")])
        if not exe:
            raise RuntimeError(f"{fmt} tool not found")
        add = [exe, "a", "-t7z", "-mx=5", tmp, folder] if fmt == "7z" else [exe, "a", "-r", "-ep1", "-m3", "-idq", tmp, folder]
        subprocess.run(add, check=True, capture_output=True, cwd=os.path.dirname(folder))
        if fmt == "rar" and not os.path.exists(tmp) and os.path.exists(tmp + ".rar"):
            os.replace(tmp + ".rar", tmp)
        subprocess.run([exe, "t", tmp], check=True, capture_output=True)
    os.replace(tmp, out)


def archives(ws, log=print):
    cfg = ws.config()
    fmt = cfg["archive_format"]
    if fmt in ("7z", "rar") and not (find_tool(["7z", "7zz", "7za"], [os.path.join("7-Zip", "7z.exe")]) if fmt == "7z"
                                     else find_tool(["rar"], [os.path.join("WinRAR", "Rar.exe")])):
        log(f"  {fmt} tool not found: using zip")
        fmt = "zip"
    done = []
    for name in sorted(os.listdir(ws.backup)):
        folder = os.path.join(ws.backup, name)
        if not os.path.isdir(folder) or name.startswith("_"):
            continue
        out = os.path.join(ws.backup, f"{name}.{fmt}")
        if os.path.exists(out) and os.path.getmtime(out) > _newest(folder):
            done.append((out, "up to date"))
            continue
        log(f"  packing {name}.{fmt}…")
        archive_one(folder, out, fmt)
        done.append((out, f"{os.path.getsize(out) / 2**20:.1f} MB, tested"))
    return done


# ── coverage page ─────────────────────────────────────────────────────────────────────────────────────────────────
CSS = """:root{color-scheme:light dark;--bg:#f6f7f9;--panel:#fff;--fg:#1a1d23;--mut:#5b6472;--line:#dde1e7;--ok:#166534;--part:#92400e;--no:#b91c1c;--acc:#2457c9}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--panel:#1d2026;--fg:#e8eaee;--mut:#9aa3b0;--line:#2c313a;--ok:#86efac;--part:#fbbf24;--no:#fca5a5;--acc:#8fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
p.sub{color:var(--mut);margin:0 0 16px}a{color:var(--acc)}.sum{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 4px}
.sum div{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px}.sum b{display:block;font-size:18px}
.tbl{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:640px;table-layout:fixed}th:first-child{width:32%}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--mut);font-weight:600}tr.file td{font-weight:600;background:color-mix(in srgb,var(--line) 35%,transparent)}
td.pg{padding-left:26px}.ok{color:var(--ok)}.part{color:var(--part)}.no{color:var(--no)}.mut{color:var(--mut)}small{color:var(--mut)}"""


def _mark(ok, total, empty=0, label="empty"):
    if not total:
        return '<span class="mut">—</span>'
    note = f' <small>+ {empty} {label}</small>' if empty else ""
    if ok + empty >= total:
        return f'<span class="ok">✔ {ok}</span>{note}'
    return f'<span class="{"part" if ok else "no"}">{"◐" if ok else "✖"} {ok}/{total - empty}</span>{note}'


def coverage(ws):
    cfg = ws.config()
    inv = read_json(os.path.join(ws.station, "inventory.json"), {"files": {}})
    sel = read_json(os.path.join(ws.station, "pages.json"), {})
    st = ws.state().get("files", {})
    cp = read_json(copies.path(ws), {"items": {}})["items"]
    dr = read_json(os.path.join(ws.station, "drift.json"), {"files": {}})
    esc = html.escape
    cols = cfg["formats"] + (["tokens"] if cfg["addons"].get("tokens") else [])
    tot = Counter()
    body = []
    queue = _plan(ws)["queue"]
    for proj in dict.fromkeys(q["project"] for q in queue):
        rows = []
        for q in [x for x in queue if x["project"] == proj]:
            tot["files"] += 1
            idx = os.path.join(ws.backup, q["dir"], "index.html")
            gal = (f'<a href="{"/".join(quote(p) for p in q["dir"].replace(os.sep, "/").split("/"))}/index.html">gallery</a>'
                   if os.path.exists(lp(idx)) else "")
            c = cp.get(q["key"])
            if not c or cfg["local_copies"] == "skip":
                lc = '<span class="mut">—</span>'
            elif c["status"] == "done":
                lc = f'<span class="ok">✔ {os.path.splitext(c["target"])[1]}</span> <small>{c["done"][:10]}</small>'
                tot["copies"] += 1
            else:
                lc = f'<span class="no">✖ {esc(c["status"])}</span>'
            d = dr["files"].get(q["key"])
            state = ""
            if d and d["edited_after"]:
                state = f'<span class="no">⚠ edited in Figma {esc(d["figma_now"][:16].replace("T", " "))} UTC, after this backup</span>'
            elif d:
                state = f'<span class="ok">current as of {esc(dr["checked"][:16].replace("T", " "))}</span>'
            exp = st.get(q["key"], {})
            when = f'<small>exported {exp["exported"][:10]}</small>' if exp.get("exported") else ""
            kind = {"figma": "Design", "figjam": "FigJam", "slides": "Slides", "make": "Make"}.get(q["editorType"], q["editorType"])
            rows.append(f'<tr class="file"><td>{esc(q["name"])} <small>{kind}</small></td><td>{lc}</td>'
                        f'<td colspan="{len(cols) + 1}">{gal} {when}</td><td>{state}</td></tr>')
            sc = read_json(screens_path(ws, q["key"]))
            pages = (inv["files"].get(q["key"]) or {}).get("pages") or [] if q["editorType"] == "figma" else []
            empties = set(exp.get("empty_ids") or [])
            tu = (read_json(os.path.join(ws.backup, q["dir"], "tokens-usage.json")) or {}).get("screens", {})
            for p in pages:
                if divider_label(p["name"]) is not None:
                    continue
                choice = (sel.get(q["key"], {}).get("pages", {}).get(p["id"]) or {})
                if not choice.get("export"):
                    why = choice.get("why", "")
                    rows.append(f'<tr><td class="pg">{esc(p["name"])}</td><td></td>'
                                f'<td colspan="{len(cols) + 2}" class="mut">not backed up{" (" + esc(why) + ")" if why not in ("", "rule") else ""}</td></tr>')
                    continue
                shots = [s for s in (sc or {}).get("screens", []) if s["pid"] == p["id"]]
                tot["pages"] += 1
                tot["screens"] += len(shots)
                cells = []
                for ext in cols:
                    if not sc:
                        cells.append("<td><span class=no>✖ not yet</span></td>")
                        continue
                    if ext == "tokens":
                        n = sum(tu.get(s["id"], {}).get("svg") in ("ok", "raw") for s in shots)
                        e = sum(tu.get(s["id"], {}).get("svg") == "none" for s in shots)
                        cells.append(f"<td>{_mark(n, len(shots), e, "no SVG") if tu else '<span class=mut>—</span>'}</td>")
                        continue
                    n = sum(os.path.exists(lp(target(ws, sc, s, ext))) or
                            (ext == "svg" and os.path.exists(lp(target(ws, sc, s, "pdf")))) for s in shots)
                    e = sum(s["id"] in empties for s in shots) if ext == "svg" else 0
                    cells.append(f"<td>{_mark(n, len(shots), e)}</td>")
                rows.append(f'<tr><td class="pg">{esc(p["name"])}</td><td></td><td>{len(shots) if sc else "—"}</td>'
                            f'{"".join(cells)}<td></td></tr>')
        head = "".join(f"<th>{'Tokens' if e == 'tokens' else e.upper()}</th>" for e in cols)
        body.append(f'<h2>{esc(proj)}</h2><div class="tbl"><table><thead><tr><th>File / page</th><th>Local copy</th>'
                    f'<th>Screens</th>{head}<th>State</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    arch = [f for f in sorted(os.listdir(ws.backup)) if os.path.splitext(f)[1] in (".zip", ".7z", ".rar")] if os.path.isdir(ws.backup) else []
    summary = (f'<div><b>{tot["files"]}</b>files</div><div><b>{tot["pages"]}</b>pages backed up</div>'
               f'<div><b>{tot["screens"]}</b>screens</div>'
               + (f'<div><b>{tot["copies"]}</b>local copies</div>' if cfg["local_copies"] != "skip" else "")
               + (f'<div><b>{len(arch)}</b>archives</div>' if arch else ""))
    page = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Backup coverage</title><style>{CSS}</style></head><body><main>'
            f'<h1>Backup coverage</h1><p class="sub">What this backup holds. Built {esc(now_iso()[:16].replace("T", " "))} by figma-offline-kit.</p>'
            f'<div class="sum">{summary}</div>{"".join(body)}'
            + (f'<h2>Archives</h2><ul>{"".join(f"<li><a href={quote(a)!r}>{esc(a)}</a></li>" for a in arch)}</ul>' if arch else "")
            + "</main></body></html>\n")
    out = os.path.join(ws.backup, "COVERAGE.html")
    write_text(out, page)
    return out


def render(v, d=None, arch=None, cov=None):
    t = v["totals"]
    lines = ["# Close", "", f"Checked {v['checked']}.", "",
             f"- Files exported: {t.get('files', 0)} · screens {t.get('screens', 0)}"
             + "".join(f" · {k.upper()} {t.get(k, 0)}" for k in ("png", "svg") if k in t)
             + (f" · PDF instead of SVG {t['pdf']}" if t.get("pdf") else "")
             + (f" · empty frames {t['empty']}" if t.get("empty") else "")]
    cps = {k[5:]: v_ for k, v_ in t.items() if k.startswith("copy ")}
    if cps:
        lines.append("- Local copies: " + " · ".join(f"{k} {n}" for k, n in sorted(cps.items())))
    if d is not None:
        ch = [x["name"] for x in d["files"].values() if x["edited_after"]]
        lines.append(f"- Drift: {len(d['files'])} files checked · "
                     + (f"**changed in Figma since the backup: {', '.join(ch)}** (run `python kit.py refresh`)" if ch else "all current"))
    if cov:
        lines.append("- Coverage page: [COVERAGE.html](../backup/COVERAGE.html)")
    for out, note in arch or []:
        lines.append(f"- Archive: {os.path.basename(out)} ({note})")
    lines += ["", f"**Problems: {len(v['problems'])}**"] + [f"- {p}" for p in v["problems"]]
    return "\n".join(lines) + "\n"
