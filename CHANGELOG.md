# Changelog

## 1.2.0 (2026-11-01)

- **Two downloads:** `figma-offline-kit-windows.zip` and `figma-offline-kit-macos.zip` on the website, each with one start file, a short bilingual *Read me first* page, `app/` (the kit) and `guides/`. AI users keep using the GitHub repo.
- **Python install offer:** when Python 3.10+ is missing, `Start.bat` offers to install it with winget (Windows) and `Start.command` with Homebrew or the python.org installer (macOS). Both ask first; nothing is installed without a yes. Python installed for your user is found even before PATH updates.
- **Persian or English:** `kit.py start` asks the language first (`--lang fa|en` skips the question) and remembers it in the settings; the questions and messages of the guided start are in both languages. Windows terminals can't lay out right-to-left text, so it shows a Persian test line there and switches to English if it reads badly.
- **Token step:** the guided start shows exactly where the token goes (`<workspace>/workstation/.env`), lets you paste it hidden right there or opens the file in Notepad or TextEdit, and checks it with Figma before going on.
- Doctor explains the macOS certificate error that a fresh python.org install can give.
- **`Figma token.txt`** next to Start in the downloads: paste the token there if you like; Start moves it into the workspace `.env` and empties the txt.
- **`REPORT.md` moved to the top of the backup folder** (it moves itself from `workstation/`), with your settings as plain decisions in your language and a dated **Log** of every step and decision and who made it. `COVERAGE.html` links to it.
- **Guided start for people without an AI:** a short ✔ / ✖ checklist instead of the doctor tables (optional items shown as "optional, off"), no command hints, progress and a pause question when a backup is running, the backup runs in full by default, and local copies are offered as "later, you press Save" (default: not now).
- Text in the guided start and the terminal interview wraps to the window (76 columns at most); a wrong option number asks again.
- Start says "Extract the ZIP first" when Windows runs it from inside the ZIP.
- Sizes under 1 GB in MB, and "1 file" / "2 files".
- **Better screen estimates:** the scan now counts the frames inside sections (nested ones too, one small call per file with sections) and skips hidden frames, instead of guessing 6 per section.
- Start on later runs: one line when everything is still ready; the close step in plain text; at the end it offers the coverage page (which links every gallery) and the backup folder.
- Read me, README and site: what to click when Windows or macOS warns about a file from the internet, and how to skip Windows' warning (ZIP → Properties → Unblock).
- **Live progress in Start:** after "Start the backup" the window stays open and shows the current file, PNG / SVG counts, time so far and time left, and a line per finished file. Closing it doesn't stop the backup. When Figma can't be reached it says so (check your internet or VPN) with a countdown; **R** retries at once, **P** pauses, Enter stops watching. Failed files: "Retry them now?". When the export ends it goes straight on to checking and packing.
- **Persian on Windows:** Windows terminals show Persian reversed and unjoined, so the Start window stays in English there; choosing Persian makes the report and pages Persian. Elsewhere Start is fully Persian, with Persian digits (typed answers accept both), a Persian checklist and page list.
- `Figma token.txt` ends with a `FIGMA_TOKEN=` line, as Start's instructions say; a token pasted anywhere in the file is found.
- Plainer wording when Figma can't be reached: "Can't reach Figma: check your internet or VPN".
- **No more hanging downloads:** every read from Figma (API and image server) has a total deadline as well as an idle timeout, so a stalled connection fails and is tried again instead of hanging; pausing (P, or `kit.py stop`) takes effect within seconds, even mid-batch or during a wait. The live view says "No new screen for N min" instead of showing a frozen line.
- **REPORT.md in Persian:** with Persian chosen, every section (title, log, settings, check, plan, pages, run, close) is Persian with Persian digits, inside a right-to-left block for GitHub and VS Code previews. The log comes first, newest on top.
- The live view keeps the last time-left estimate ("… · waiting…") while nothing is downloading, instead of counting up.
- **A new copy of the kit continues your backup:** give Start the folder of an existing backup and it says what it found (files, screens done) and offers to continue it with its settings, without asking the setup questions again.
- **Release downloads:** publishing a release on GitHub attaches `figma-offline-kit-<version>-windows.zip` and `-macos.zip`, built from that tag by a GitHub Action (`.github/workflows/release-downloads.yml`). A tag without a release gets nothing; the Action can also be run by hand for an existing release.
- Site: icons on the buttons (demo, GitHub, Windows, macOS).

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
