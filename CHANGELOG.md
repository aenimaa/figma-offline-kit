# Changelog

## 1.1.0 (2026-11-01)

- **Double-click start:** `start.bat` (Windows) and `start.command` (macOS, Linux) find Python, or open its download page, then run the new `python kit.py start`: a guided walk through setup, check, scan, pages and backup that picks up where you left off.
- **`doctor --redact`** hides your folders and Figma name, so the output can go into a public issue.
- **Issue template** that asks for the redacted doctor output.
- **README:** download-and-double-click first, which AI apps can run the kit, which Figma plan you need, and when you'd need a backup.
- **Live demo site** at aenimaa.github.io/figma-offline-kit, in Persian and English.

## 1.0.1 (2026-10-30)

- A more visual README in English and Persian, with screenshots of the gallery, tokens, handoff and coverage page.
- The demo team is now a made-up app ("Bloom") with real-looking screens, plus a demo dev handoff in `examples/handoff/`.
- Gallery: the full-screen viewer has a solid background, so the page behind no longer shows through.
- `kit.py pages` says "1 screen", not "1 screens".

## 1.0.0 (2026-10-29)

First public release.

- **Setup:** `doctor` checks Python, network, token, team or files, Figma desktop and optional tools, and lists what's ready and what you need to do. One-round interview (`questions`, `init`), by AI or in the terminal.
- **Scope:** a whole team, or single files by link. Page rule (all except archive pages, named pages, or pick) and a page-selection step (`pages`) that the run waits for.
- **Export:** `plan` with estimates; `run` / `resume` / `stop` / `status`. Runs in the background and survives closing the app. Modes: full, project by project, file by file. PNG and SVG per frame, PDF where Figma can't render SVG, large frames below @2x. Paced calls, full Retry-After, outages waited out.
- **Offline gallery** per file: grid, canvas map, page tree, filters, viewer, links to Figma.
- **Local copies** (`copies`): `.fig` / `.jam` / `.deck` / `.make` from Figma desktop, guided or automatic, paced at ≈ 40 a day, checked and filed.
- **Design tokens** (`tokens`): variables from REST (Enterprise), Figma's MCP, or Figma's native export; `tokens.css` / `_tokens.scss`; per-screen token report; token SVGs; token panel in the gallery.
- **Dev handoff** (`handoff`): fresh screens, tokens, Figma design-to-code via Figma desktop's MCP server, component anatomy, used-by, per-frame pages.
- **Close** (`close`, `refresh`): verify, drift check, `COVERAGE.html`, tested archives (zip, 7z or rar); changed files re-exported without deleting anything.
- Guides in English and Persian. Python 3.10+, standard library only. MIT.
