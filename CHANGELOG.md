# Changelog

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
