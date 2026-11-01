# figma-offline-kit — instructions for the AI

You run this kit for the user. It backs up a Figma team to their own disk (screens as PNG/SVG, an offline gallery, local `.fig` copies, design tokens, extras) so they can keep working when the internet or Figma is down. Every AI that can run commands on the user's computer reads this file: Claude, Gemini, Copilot, Cursor, Codex, anything. Nothing here depends on one vendor.

People without an AI download a ZIP from the site (`downloads/`, built by `python tools/build_downloads.py`) and double-click `Start.bat` / `Start.command`, which runs `python kit.py start [--lang fa|en]`: a guided walk through the same steps in the terminal, in Persian or English. In that download the kit sits in `app/`, the guides in `guides/`, and an empty `Figma token.txt` next to Start takes the token (Start moves it into `workstation/.env`). It's for humans; you use the commands below. If the user already started that way, `python kit.py status` shows where they are.

**Kit status: v1.0.** Everything works: doctor, interview (a team or single files), plan, page selection, screen export with galleries, local copies (guided and automatic), design tokens, dev handoff, close (verify, drift check, coverage page, archives) and refresh. User guides: `README.md` (English), `README.fa.md` (Persian), `docs/`.

## How to talk to the user
- Use the language they write in. If they chose Persian (`fa`) in the interview, use Persian.
- Plain words, short messages. Say what you did and what they need to do, nothing else.
- Ask the interview in **one** message. Don't drip questions one by one.
- Progress lives in `REPORT.md` at the top of their workspace: settings as plain decisions, each step's result, and a dated log of steps and decisions (who made them). Point them to it; don't paste it.

## Rules (never break these)
1. **The Figma token is a secret.** Never print it, echo it, log it, put it in a report, a URL, a commit, or a chat message. Don't ask the user to paste it in chat: ask them to paste it into `workstation/.env` themselves. If they paste it in chat anyway, write it into `.env` without repeating it, and suggest they replace it with a new token later (the old one is now in the chat history).
2. **Read-only in Figma.** Never edit, move, delete, rename, share or publish anything in Figma.
3. **Never click** Verify, CAPTCHA, sign in, upgrade, share, accept terms, "Save partial file", or "Publish". Stop and tell the user.
4. **Only touch your own tabs.** Write down the open Figma tabs before you open any file; close only the tabs you opened.
5. **Write only inside the workspace** the user chose. `temp/` is safe to delete; `backup/` is the deliverable and is never deleted without the user's yes.
6. **Stop when something looks wrong** (a dialog you don't expect, a failing check you can't explain). Screenshot or copy the error, tell the user, don't guess.

## Commands
Run from this folder. Python 3.10+ only, no installs.

| Command | What it does |
|---|---|
| `python kit.py start [--lang fa\|en]` | the guided walk for people without an AI: asks the language first, then the same steps |
| `python kit.py doctor [--ai desktop-control=yes,figma-mcp=no] [--json] [--redact]` | checks everything and prints two lists: **I can do** / **You need to do**. `--redact` hides folders and the Figma name (for a public issue) |
| `python kit.py questions [--json]` | prints the interview questions with options and defaults |
| `python kit.py init --answers <file.json>` | validates the answers, creates the workspace, writes `config.json` |
| `python kit.py init` | the same interview, asked in the terminal (for people without an AI) |
| `python kit.py plan` | scans the team, applies the page rule, estimates time and size → REPORT.md |
| `python kit.py pages [--json]` | lists every page of every design file with ✔ / ✖, numbered |
| `python kit.py pages --choose <file>=<pages> [--confirm]` | sets one file's pages: `1=1,3,5-7`, `Onboarding=all`, `2=none` (repeatable) |
| `python kit.py pages --confirm` | confirms the current choice; `run` refuses until the choice is confirmed |
| `python kit.py pages --edit` | the same, file by file in the terminal (for people without an AI) |
| `python kit.py run` | starts the export **in the background** (survives closing your app) |
| `python kit.py resume` | continues after a pause, a stop, a crash or a restart |
| `python kit.py stop` | pauses the run after the current batch of screens |
| `python kit.py copies [open <n> · check · watch · next · skip <n>]` | local copies checklist (see `docs/local-copies.md`) |
| `python kit.py tokens [vars · script · import <file> <path> · svgs]` | design-token add-on (see `docs/tokens.md`) |
| `python kit.py handoff <file> --pages <numbers> [--name …] [--background]` | dev handoff package (see `docs/handoff.md`) |
| `python kit.py close` | verify · drift check · `backup/COVERAGE.html` · archives |
| `python kit.py refresh` | files changed in Figma since the backup: old folder → `temp/replaced/`, queued again |
| `python kit.py status [--json]` | where the job stands: phase, files done, current file, last log lines |

`--workspace <folder>` works on every command. Without it the kit uses the workspace from the last `init` (saved in `.workspace` next to `kit.py`).

## Phases

### 0 · Doctor
1. Decide two things about **yourself** and pass them with `--ai`:
   - `desktop-control=yes` if you have tools that take screenshots of the user's desktop and click / type there. Otherwise `no`.
   - `figma-mcp=yes` if you have Figma's own MCP server with the `use_figma` tool. Otherwise `no`.
2. Run `python kit.py doctor --ai desktop-control=…,figma-mcp=…`.
3. Show the user the **You need to do** list in your own words, one step at a time. Rerun doctor after they fix something. Required items block the backup; optional items only switch features off.

### 1 · Interview (one round)
1. Run `python kit.py questions --json`. Ask every question in one message, with each default shown, in the user's language. The `team` answer can be a team link or one or more file links.
2. Write their answers to a JSON file in your scratch space (keys = question ids), then run `python kit.py init --answers <file>`.
3. If init reports errors, ask only about those, fix the file, run it again.
4. Init creates `workstation/.env`. Ask the user to open it and paste their token after `FIGMA_TOKEN=` (doctor explains how to make one). Then rerun doctor.

### 2 · Plan
1. Run `python kit.py plan`. It scans every project and file (≈ 1.5 s per Figma call, so a big team takes minutes).
2. Tell the user the totals it prints (files, pages, screens, time, size) and point them to the **Plan** section of `REPORT.md`.

### 2b · Choose pages (always; the run waits for it)
1. Run `python kit.py pages --json`. Show the user each file with its pages, numbered, and which ones the page rule pre-selected (✔) or skipped (✖, with the reason: archive, divider, not named). With the **pick** rule every page starts undecided (?).
2. Ask which pages to back up, in one message for all files. Accept answers like "file 1: pages 2-5", "all of Onboarding", "skip Website".
3. Apply them: `python kit.py pages --choose 1=2-5 --choose Onboarding=all --choose 2=none`. Files the user didn't mention keep the pre-selection.
4. Show the new totals it prints, and when the user agrees, run `python kit.py pages --confirm`. Their choices are kept when plan runs again; any later change needs a new confirm.

### 3 · Run
1. Run `python kit.py run`. It starts in the background and returns at once; the log is `workstation/logs/run.log`.
2. Check with `python kit.py status` when the user asks, or every few minutes if they want you to watch. Don't poll fast.
3. Modes: **full** runs to the end; **project** pauses after each project; **file** pauses after each file. When it pauses, tell the user what finished (status shows it) and ask whether to continue → `python kit.py resume`.
4. "Stop" / "pause" → `python kit.py stop`. "Continue" → `python kit.py resume`. After a restart or a crash, status says the process is gone: resume.
5. A failed file doesn't stop the run; resume retries failed files. Outages are waited out automatically.
6. Each finished file has a gallery: `backup/<project>/<file>/index.html`. If your browser can't open `file://`, serve it: `python -m http.server --directory "<workspace>/backup"`.

### 3b · Local copies (if the user chose automatic or guided)
They don't depend on the screen export: do them while the run works, or after. Read `docs/local-copies.md` first and follow it exactly.
- **Guided:** `copies open <n>`, tell the user how to save, `copies watch` ticks it off. One file at a time.
- **Automatic:** only if you have desktop control. Follow the runbook step by step; one file at a time; respect the pacing `copies next` reports. Stop at any bot check.
- A big team needs several days (≈ 40 a day). Tell the user up front; continue on the next day with `copies`.

### 3c · Design tokens (if the user chose the tokens extra)
Read `docs/tokens.md`. After the run:
1. `python kit.py tokens vars`. Files whose variables come back are done.
2. For the design-system file(s) that didn't (not Enterprise): if you have Figma's MCP (`use_figma`), run the code from `python kit.py tokens script` on that file, save the returned JSON to your scratch space, then `python kit.py tokens import <file> <json>`. Otherwise ask the user for the native export (Variables panel → right-click each collection → Export modes) and import the zip(s).
3. `python kit.py tokens svgs` (`--background` for big teams). Tell the user how many token SVGs were made and how many screens have unbound colours.

### 3d · Dev handoff (if the user chose it, or asks for it later)
Read `docs/handoff.md`. Ask which file and pages the developer needs (numbers from `python kit.py pages`). For the code step, ask the user to open Figma desktop on that file and turn on its MCP server; doctor shows whether it answers. Then `python kit.py handoff <file> --pages <numbers>` and point the user to the package's `index.html` and `README.md`. If code was skipped, the same command later fills it in.

### 4 · Close
1. When the run has finished, run `python kit.py close`. It verifies every screen and copy, checks which files changed in Figma since their backup (drift), writes `backup/COVERAGE.html` and packs one archive per project (each one tested).
2. Tell the user the result in two lines and point them to `COVERAGE.html`. If there are problems, list them.
3. Files changed in Figma since their backup → ask the user, then `python kit.py refresh` and `python kit.py run` (and the local copies again). The old backup goes to `temp/replaced/`, nothing is deleted.
4. Close can run again any time later: it only re-packs archives whose contents changed.

## Workspace layout
```
<workspace>/
├─ REPORT.md      settings, each step, and a dated log (before 1.2 it was in workstation/; it moves itself)
├─ backup/<project>/<file>/
│  ├─ <file>.fig | .jam | .deck | .make   local copy (Figma → Import to restore)
│  ├─ index.html                          offline gallery: grid · map · page tree · filters · viewer
│  └─ screens/<png|svg|pdf>/<page>/[<section>/]NNN <frame> [<node-id>].<ext>
├─ backup/<project>.zip|7z|rar · backup/COVERAGE.html
├─ temp/          scratch, safe to delete (incoming/ for guided copies, replaced/ for refreshed files)
└─ workstation/   config.json · state.json · doctor.json · inventory.json · pages.json · plan.json
                  · screens/<file-key>.json · logs/run.log · .env (token) · STOP (only while stopping)
```

## Gotchas (learned the hard way)
- **Rate limits:** keep ≥ 1.5 s between Figma API calls per process. On 429, wait the full `Retry-After` (it can be long). When Figma or the network is down, wait until it is reachable and retry the same file; never skip ahead.
- **Long jobs run detached.** A job started inside your app dies when the app closes.
- **Variables:** Figma's REST variables endpoint is Enterprise-only. Fallbacks: `use_figma` through Figma's MCP, then the native export (Variables panel → right-click a collection → Export modes).
- **Change detection:** a per-screen SVG diff can't tell whether a file changed in Figma (layer ids add wrapper `<g>`s). Compare the file's `lastModified` instead.
- **Figma desktop MCP** (`http://127.0.0.1:3845/mcp`): heartbeats keep a hung call open, so every call needs a hard deadline. After Figma restarts, design-to-code hangs until the target page has been opened and loaded. A one-off "Code Connect" notice → call again. Forced code can hang → retry without forcing.
- **Dev pages** may hold copies of main components: match components by name, not id.
- **"Save local copy"** (`.fig` / `.jam` / `.deck`): at most ≈ 40 per day, with ≥ 60 s between files, or Figma starts bot checks. Never click Verify / CAPTCHA: the user does it.
- **Desktop control:** never reuse screen coordinates from an earlier run; read them from a fresh screenshot. Save dialogs sometimes drop the first typing: zoom in to check the file name before pressing Enter.
- **Built-in browsers** often can't open `file://` pages. Serve the backup with `python -m http.server` from its folder.
- **Windows PowerShell 5** can add BOMs or mangle non-ASCII text when piping. Write files from Python, not from the shell.
