# Dev handoff

A self-contained package for the pages a developer needs, made fresh from Figma, in `<workspace>/handoff/<name>/`. The backup is never touched.

```
python kit.py pages                                  # find the file and page numbers
python kit.py handoff 1 --pages 3                    # file 1, page 3 (add --background for big pages)
python kit.py handoff Onboarding --pages 2-4 --name "Sign-up v2"
```

| Step | What you get | Needs |
|---|---|---|
| screens | fresh PNG + SVG of every frame (numbers match the backup) | token |
| tokens | token SVGs and a per-frame token report, plus `tokens/tokens.css` | variables saved (`kit.py tokens`) |
| code | `code/<frame>.tsx`: Figma's own design-to-code (React + Tailwind), styles, assets | **Figma desktop open on the file, with its MCP server on** |
| anatomy | `components/<frame>.html`: properties, variants, spacing / radius / colour tokens, layer tree | token |
| used-by | which components each frame uses, and where each component is used | token |
| pages | `frames/<frame>.html`: tabs Design · Code · Tokens · Anatomy; `[M]` / `[D]` frames are linked as responsive pairs | — |
| gallery | `index.html` with a **Code & specs** link per frame, and `README.md` | — |

Everything is resumable: run the same command again and only what's missing is done. If the code step was skipped (Figma desktop closed), open Figma desktop on the file, turn on its MCP server, and run the command again.

**Turning the server on:** the local MCP server answers at `http://127.0.0.1:3845/mcp`. Its switch has moved between Figma versions (Preferences, or the Dev Mode inspect panel). Figma desktop 126 (October 2026) showed only remote MCP clients and no local switch; there the code step is skipped and everything else still works. `python kit.py doctor` shows whether the server answers.

**Code step, learned the hard way:** each frame gets a hard time limit (the server's heartbeats keep a hung call open). First pass forces full code; frames that fail get a second pass without forcing. Figma's one-off "Code Connect" prompt is answered by asking again. After Figma restarts, open the file's page once before running, or design-to-code hangs.
