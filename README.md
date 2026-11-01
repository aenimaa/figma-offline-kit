<p align="center">
  <b>English</b> · <a href="README.fa.md">فارسی</a>
</p>

<p align="center">
  <img src="docs/images/hero.png" width="100%" alt="figma-offline-kit: Figma’s down? Your work isn’t. An offline gallery showing a Figma page as a map of its frames.">
</p>

<h1 align="center">figma-offline-kit</h1>

<p align="center">
  Back up your Figma team to your own disk, and keep working when Figma or the internet is down.<br>
  <sub>Free · open source · read-only in Figma · works with any AI assistant, or on its own</sub>
</p>

<p align="center">
  <a href="https://github.com/aenimaa/figma-offline-kit/releases/latest"><img src="https://img.shields.io/github/v/release/aenimaa/figma-offline-kit?label=release&color=2457c9" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-2457c9" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/dependencies-none-2457c9" alt="No dependencies">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2457c9" alt="MIT license"></a><br>
  <sub>Windows · macOS · Linux · <a href="https://aenimaa.github.io/figma-offline-kit/">See the live demo</a> (made-up app)</sub>
</p>

---

## 🚀 Start in a minute

**You need Python 3.10 or newer** (free; the kit runs on it and installs nothing else) and a read-only **[Figma token](docs/figma-token.md)**. If Python is missing, the start file offers to install it and asks first.

| 🖱️ Double-click, no AI needed | 🤖 With an AI assistant |
|---|---|
| **1 ·** Download for **[Windows](https://aenimaa.github.io/figma-offline-kit/downloads/figma-offline-kit-windows.zip)** or **[macOS](https://aenimaa.github.io/figma-offline-kit/downloads/figma-offline-kit-macos.zip)** and unzip it.<br>**2 ·** Double-click **`Start.bat`** (Windows) or **`Start.command`** (macOS).<br><br>It asks your language (فارسی / English), walks you through every step, shows the backup's progress live, and picks up where you left off. | Get this repo: [ZIP](https://github.com/aenimaa/figma-offline-kit/archive/refs/heads/main.zip) or `git clone`. Open the folder in an AI app that **can run commands on your computer**: Claude Code or Claude desktop, Cursor, VS Code with Copilot agent mode, Gemini CLI, Codex. Say:<br><br>**“Back up my Figma team.”**<br><br>It reads [`AGENTS.md`](AGENTS.md), asks a few questions in one message, and runs the rest. |

**⌨️ In a terminal:** `python kit.py start` (add `--lang fa` for Persian) runs the same guided walk: in this repo, or in the download's `app/` folder. Step by step: `doctor` · `init` · `plan` · `pages` · `run` · `close` (see [`AGENTS.md`](AGENTS.md)).

**🔑 Where the token goes:** `<workspace>/workstation/.env`, after `FIGMA_TOKEN=`. With the default workspace that is `C:\Users\<you>\figma-backup\workstation\.env` on Windows and `~/figma-backup/workstation/.env` on macOS. The guided start prints the exact path, lets you paste the token there hidden, or opens a file for you in Notepad / TextEdit, and checks it with Figma. In the download you can also paste it into **`Figma token.txt`** next to Start: Start moves it into `.env` and empties the txt.

**📝 What happened, written down:** `REPORT.md` at the top of the backup folder lists your settings as plain decisions, each step's result, and a dated log of every step and decision.

<details>
<summary><b>What's in the download</b></summary>

```
figma-offline-kit-windows/          (or -macos)
├─ Start.bat                        double-click this (Start.command on macOS)
├─ Read me first.html               three steps, in English and Persian
├─ Figma token.txt                  paste your token here (Start moves it to a safe place)
├─ app/                             the kit: kit.py, kit/, templates/, LICENSE
└─ guides/                          token, local copies, design tokens, handoff, FAQ, troubleshooting
```

The downloads are for people without an AI. They leave out `AGENTS.md` and the AI files: **AI users work from this repo**, which has everything (and the tests).
</details>

<details>
<summary>Notes: chat-only AI, security warnings, Linux, Persian in terminals</summary>

- **Chat-only AI** (ChatGPT or Claude in a browser tab) can't run the kit: it can't run commands on your computer. Use the double-click way instead.
- **macOS blocks `Start.command` the first time** because it was downloaded: open System Settings → Privacy & Security → *Open Anyway*, or run `bash Start.command` in Terminal.
- **Windows warns about files from the internet.** To skip it: before unzipping, right-click the ZIP → *Properties* → tick *Unblock* → *OK*. Otherwise click *Run* on "Open File – Security Warning … Are you sure you want to run this software?", or *More info* → *Run anyway* on "Windows protected your PC".
- **Linux:** run `bash start.command` in this repo.
- **Persian on Windows:** Windows terminals show Persian reversed and unjoined, so there the Start window stays in English; choosing Persian makes the report (`REPORT.md`) and the pages Persian. On macOS the window can be Persian too.
</details>

## 🧭 When you'd need it

- **Figma or the internet is down**, and you still need the screens today.
- **You lose access:** you leave a team or a client, a plan is downgraded, or an account is blocked.
- **A developer needs specs** without a Figma seat.
- **A record of a date:** what existed at a handover or a release, with a coverage page to prove it.

## 📦 What you get

### 🗺️ An offline gallery for every file

Every frame as **PNG and SVG**, in folders by project, file, page and section. Browse them like the canvas: a map of where each frame sits, a page tree, filters, search, and a full-screen viewer. It opens from disk, no internet needed.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/gallery-map-dark.png">
  <img src="docs/images/gallery-map-light.png" width="100%" alt="The offline gallery in map view: the Sign up section with Welcome, Email and Email taken screens, and Home beside it, laid out as on the Figma canvas.">
</picture>

### 🎨 Design tokens next to every screen

Your variables as `tokens.css` and `_tokens.scss`. For each screen, the tokens and styles it uses, and the colours bound to nothing. Token SVGs keep the picture and write colours as `var(--token, #hex)`. [More](docs/tokens.md)

<img src="docs/images/viewer-tokens.png" width="100%" alt="The gallery viewer showing the Welcome screen, with a Tokens used panel listing --brand #5A78DC and --color-bg #EEEEFF.">

### 🧩 A handoff package for developers

For the pages a developer needs: one page per frame with **Design · Code · Tokens · Anatomy**, Figma's own design-to-code output, and component specs. [More](docs/handoff.md)

<img src="docs/images/handoff-code.png" width="100%" alt="A handoff frame page for Welcome with the Code tab open, showing React and Tailwind code that uses var(--brand).">

### ✅ Proof of what you have

`COVERAGE.html` shows every project, file and page: what's backed up, what's left out and why, and which files changed in Figma since. Each project is packed into a tested archive.

<img src="docs/images/coverage.png" width="100%" alt="The coverage page: files and pages with PNG, SVG and token counts, and a 'current as of' state for each file.">

### 💾 And the real files

Local **`.fig` / `.jam` / `.deck`** copies from Figma desktop, saved for you by an AI with desktop control, or with you pressing Save. Paced so Figma's bot checks don't kick in. [More](docs/local-copies.md)

## 💳 Which Figma plan you need

| What | Plan | Notes |
|---|---|---|
| Screens (PNG, SVG), offline gallery, coverage page, archives | any | a token with read scopes |
| Local `.fig` / `.jam` / `.deck` copies | any | Figma desktop |
| Design tokens by the REST API | Enterprise | other plans: Figma's MCP or Figma's own variables export ([tokens](docs/tokens.md)) |
| Dev handoff | any | the code step needs Figma desktop's MCP server ([handoff](docs/handoff.md)) |

## ⚙️ How it works

| | Step | What happens |
|---|---|---|
| 1 | **Doctor** | checks Python, network, token and tools; lists what's ready and what you need to do |
| 2 | **Questions** | one round: a team link or file links, where to save, how to run, which pages and extras |
| 3 | **Plan** | scans Figma and estimates screens, time and size |
| 4 | **Pages** | every page with ✔ or ✖; archive and divider pages are left out until you say otherwise |
| 5 | **Run** | exports in the background, survives closing the app, waits out outages, resumes |
| 6 | **Close** | verifies everything, flags files changed in Figma, writes the coverage page, packs archives |

<details>
<summary><b>📁 What ends up on your disk</b></summary>

```
<workspace>/
├─ REPORT.md          your settings, each step and a dated log of decisions
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
└─ workstation/       settings · logs · .env (your token)
```

If a browser won't open `file://` pages, serve the folder: `python -m http.server --directory "<workspace>/backup"`.
</details>

## 🔒 Safe by design

- **Read-only in Figma.** It never edits, moves, shares or deletes anything there.
- **Your token stays on your disk**, in `workstation/.env`. It's never printed, logged or put in a report.
- **Polite to Figma:** at least 1.5 s between calls, rate limits honoured in full, about 40 local copies a day.
- **Nothing is deleted.** Refreshed files move to `temp/replaced/`.

## 📚 Docs

[Figma token](docs/figma-token.md) · [Figma MCP servers](docs/figma-mcp.md) · [Local copies](docs/local-copies.md) · [Design tokens](docs/tokens.md) · [Dev handoff](docs/handoff.md) · [FAQ](docs/faq.md) · [Troubleshooting](docs/troubleshooting.md) · [Changelog](CHANGELOG.md)

---

<p align="center"><sub>MIT license · Vibe-coded by <a href="https://github.com/aenimaa">Nima Sh</a>, a product designer who didn’t want an outage to stop his work</sub></p>
