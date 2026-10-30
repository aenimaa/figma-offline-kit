"""Page selection: show every page of every design file and let the user choose which ones to back up.

The interview's page rule makes the first suggestion; this step is where the user sees it and changes it.
The run starts only after the user has confirmed the current choice (plan.json pages_hash)."""
import os

from . import plan
from .names import divider_label
from .util import read_json, write_json

MARK = {True: "✔", False: "✖", None: "?"}


def load(ws):
    return (read_json(os.path.join(ws.station, "inventory.json")), read_json(os.path.join(ws.station, "pages.json"), {}))


def files(ws):
    """Design files in plan order: [(number, key, record from pages.json, pages in Figma order)]."""
    inv, sel = load(ws)
    p = read_json(os.path.join(ws.station, "plan.json"), {"queue": []})
    out = []
    for q in p["queue"]:
        if q["key"] in sel:
            counts = {pg["id"]: pg.get("counts", {}) for pg in inv["files"][q["key"]]["pages"]}
            pages = [(pid, dict(sel[q["key"]]["pages"][pid], est=plan.page_estimate(counts[pid])))
                     for pid in counts if pid in sel[q["key"]]["pages"]]
            out.append((len(out) + 1, q["key"], sel[q["key"]], pages))
    return out


def render(ws):
    lines = ["# Pages", "", "✔ backed up · ✖ skipped · ? not decided yet. Numbers are used to choose pages.", ""]
    for n, key, rec, pages in files(ws):
        lines.append(f"## {n}. {rec['project']} / {rec['file']}")
        lines.append("")
        for i, (pid, p) in enumerate(pages, 1):
            why = "" if p["why"] in ("rule", "named", "pick") else f"  ({p['why']})"
            lines.append(f"{i:>3}. {MARK[p['export']]} {p['name']}{why}" + (f"  · ≈ {p['est']} screen{'s' if p['est'] != 1 else ''}" if p["est"] else ""))
        lines.append("")
    return "\n".join(lines)


def find_file(ws, ref):
    """A file by its number in the list, its key, or its name (case-insensitive)."""
    fl = files(ws)
    for n, key, rec, pages in fl:
        if ref == str(n) or ref == key or ref.casefold() == rec["file"].casefold():
            return key, pages
    raise ValueError(f"no design file '{ref}' (use its number from `kit.py pages`, its name or its key)")


def parse_numbers(spec, count):
    spec = spec.strip().lower()
    if spec == "all":
        return set(range(1, count + 1))
    if spec in ("none", "-"):
        return set()
    out = set()
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        a, _, b = part.partition("-")
        lo, hi = int(a), int(b or a)
        if not (1 <= lo <= hi <= count):
            raise ValueError(f"page number {part} is outside 1-{count}")
        out.update(range(lo, hi + 1))
    return out


def choose(ws, ref, spec):
    """Set exactly these pages (numbers, ranges, 'all', 'none') of one file to be backed up."""
    key, pages = find_file(ws, ref)
    pick = parse_numbers(spec, len(pages))
    _, sel = load(ws)
    for i, (pid, _) in enumerate(pages, 1):
        sel[key]["pages"][pid].update(export=i in pick, why="you")
    write_json(os.path.join(ws.station, "pages.json"), sel)
    return key, sorted(pick)


def refresh(ws):
    """Rebuild plan.json and the plan section from the (unchanged) inventory after pages changed."""
    inv, _ = load(ws)
    p, sel = plan.build(ws, inv)
    return p, sel


def confirm(ws, p):
    ws.set_phase(ws.state().get("phase") or "planned", pages_confirmed=p["pages_hash"])


def confirmed(ws, p):
    return ws.state().get("pages_confirmed") == p.get("pages_hash")


def ask_terminal(ws, inp=input):
    """Walk through every file in the terminal. Enter keeps the current choice."""
    for n, key, rec, pages in files(ws):
        print(f"\n{n}. {rec['project']} / {rec['file']}")
        for i, (pid, p) in enumerate(pages, 1):
            div = "  (divider)" if divider_label(p["name"]) is not None else ""
            print(f"  {i:>3}. {MARK[p['export']]} {p['name']}{div}")
        now = ",".join(str(i) for i, (_, p) in enumerate(pages, 1) if p["export"]) or "none"
        while True:
            raw = inp(f"Pages to back up (numbers like 1,3,5-7 · all · none) [{now}]: ").strip()
            if not raw:
                if any(p["export"] is None for _, p in pages):
                    print("  Some pages are undecided: type the numbers to back up, or none.")
                    continue
                break
            try:
                choose(ws, key, raw)
                break
            except ValueError as e:
                print(f"  {e}")
