# figma-offline-kit

**Keep working when Figma or the internet is down.** This kit backs up your Figma team, or just the files you pick, to your own disk: every screen as an image, an offline gallery you can browse like the canvas, local `.fig` copies, your design tokens, and handoff packages for developers.

It runs with any AI assistant (Claude, Gemini, Copilot, Cursor, ChatGPT…) or on its own. Python 3.10+, standard library only, nothing to install. Windows, macOS and Linux.

[فارسی](README.fa.md)

---

## What you get

| | |
|---|---|
| **Screens** | every frame on the pages you choose, as PNG and SVG (PDF where Figma can't make an SVG), in folders by project → file → page → section |
| **Offline gallery** | one `index.html` per file: grid, a map that shows where each frame sits on the canvas, page tree, filters, a full-screen viewer, links back to Figma |
| **Local copies** | `.fig` / `.jam` / `.deck` / `.make` files saved by Figma desktop, so you can import the real file again |
| **Design tokens** | your variables as `tokens.css` / `_tokens.scss`, a per-screen report of which tokens and styles each screen uses, and SVGs whose colours point at your tokens |
| **Dev handoff** | for the pages a developer needs: per-frame pages with design, code, tokens and component anatomy |
| **Coverage and archives** | a `COVERAGE.html` page that shows what the backup holds and what changed in Figma since, plus one tested archive per project |

Try the gallery with made-up data: open [`examples/demo/Mobile App/Onboarding/index.html`](examples/demo/Mobile%20App/Onboarding/index.html) and [`examples/demo/COVERAGE.html`](examples/demo/COVERAGE.html).

## What you need

- **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/)).
- **A Figma personal access token**, read-only. [How to make one](docs/figma-token.md).
- Optional: **Figma desktop** for local copies and dev handoff code; **7-Zip** or **WinRAR** for smaller archives; an AI with **desktop control** to save local copies for you; **Figma's MCP server** in your AI to read variables without an Enterprise plan.

The kit checks all of this for you and says what's missing.

## Start with an AI

Open this folder in your AI app and say: *"Back up my Figma team."*

The AI reads [`AGENTS.md`](AGENTS.md) and walks you through it: a setup check, a handful of questions in one message, the plan, which pages to keep, then the backup. You answer questions and press Save where Figma needs a human. Claude, Gemini, Copilot and Cursor find their instructions on their own; for any other AI, tell it to read `AGENTS.md`.

## Start on your own

```
python kit.py doctor      # what's ready, and what you need to do
python kit.py init        # a few questions; creates your workspace
python kit.py plan        # what will be backed up, how long, how big
python kit.py pages       # choose the pages, then: python kit.py pages --confirm
python kit.py run         # starts in the background; keeps going if you close the window
python kit.py status      # progress  (stop / resume to pause and continue)
python kit.py close       # check everything, coverage page, archives
```

Optional steps, in any order after `run`:

```
python kit.py copies      # local .fig copies         → docs/local-copies.md
python kit.py tokens      # design tokens              → docs/tokens.md
python kit.py handoff     # a package for developers   → docs/handoff.md
```

## How it works

1. **Doctor** checks Python, the network, your token, Figma desktop and optional tools, and prints two lists: *I can do* and *You need to do*.
2. **Interview**: one round of questions. What to back up (a team link, or file links), where, how to run it (all at once, project by project, or file by file), which pages, which formats and extras.
3. **Plan** scans Figma and estimates screens, time and size.
4. **Pages**: you see every page of every file with a ✔ or ✖ and choose. Archive pages and divider pages are skipped by default. The run waits until you confirm.
5. **Run** exports in the background and survives closing the app or the AI. A failed file doesn't stop the run, outages are waited out, and `resume` continues where it stopped.
6. **Close** verifies every screen and copy, checks which files changed in Figma since the backup (`refresh` re-exports them), writes the coverage page and packs tested archives.

## Your workspace

```
<workspace>/
├─ backup/            the deliverable
│  ├─ COVERAGE.html   what the backup holds
│  ├─ <project>.zip   one tested archive per project
│  └─ <project>/<file>/
│     ├─ index.html   the offline gallery
│     ├─ <file>.fig   local copy (Figma → Import to restore)
│     ├─ screens/png · svg · pdf · svg-tokens/<page>/[<section>/]NNN <frame> [<id>].<ext>
│     └─ variables/   tokens.css · _tokens.scss · variables.figma.json
├─ handoff/<name>/    dev handoff packages
├─ temp/              scratch, safe to delete
└─ workstation/       REPORT.md (progress) · settings · logs · .env (your token)
```

Galleries open straight from disk. If a browser refuses `file://` pages, serve the folder: `python -m http.server --directory "<workspace>/backup"`.

## Safe by design

- **Read-only in Figma.** The kit never edits, moves, shares or deletes anything in Figma.
- **Your token stays on your disk**, in `workstation/.env`. It's never printed, logged or put in a report.
- **Polite to Figma's servers:** at least 1.5 s between calls, rate limits honoured in full, local copies paced at about 40 a day so Figma's bot checks don't trigger.
- **Nothing is deleted.** Refreshed files move to `temp/replaced/`.

## Docs

- [Figma token](docs/figma-token.md) · [Figma MCP servers](docs/figma-mcp.md) · [Local copies](docs/local-copies.md) · [Design tokens](docs/tokens.md) · [Dev handoff](docs/handoff.md)
- [FAQ](docs/faq.md) · [Troubleshooting](docs/troubleshooting.md)
- For AI agents: [AGENTS.md](AGENTS.md)

## License

MIT. See [LICENSE](LICENSE).
