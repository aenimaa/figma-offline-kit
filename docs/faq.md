# FAQ

**Does the kit change anything in Figma?**
No. It only reads. It never edits, moves, shares or deletes anything there.

**Do I need an AI?**
No. Double-click `start.bat` (Windows) or `start.command` (macOS) and answer the questions, or run the commands yourself (`python kit.py …`). An AI makes it a conversation, and with desktop control it can also save the `.fig` copies for you.

**Which AI apps can run it?**
Ones that can run commands on your computer: Claude Code or Claude desktop, Cursor, VS Code with Copilot agent mode, Gemini CLI, Codex. A chat in a browser tab (ChatGPT, Claude on the web) can't.

**Which plan do I need?**
Any Figma plan works for screens, galleries, local copies and handoff. Reading variables through the REST API needs Enterprise; on other plans, use Figma's MCP or Figma's own variables export ([design tokens](tokens.md)).

**How long does it take, and how big is it?**
`python kit.py plan` estimates both. As a rough guide: about 10 screens a minute for PNG + SVG, and about 0.65 MB per screen. Local copies are limited to about 40 a day, so a team of 100 files needs three days for those.

**Can I back up only some files?**
Yes. In the interview, paste file links instead of a team link. You can also choose pages per file with `python kit.py pages`.

**Which pages are skipped?**
By default, pages whose names contain *archive, old, deprecated, unused* or *trash*, and divider pages (names made of dashes). You choose in the interview and change any page with `python kit.py pages`.

**Can I close my laptop or the AI app during the run?**
Closing the app is fine: the run continues in the background. If the computer sleeps or restarts, run `python kit.py resume`.

**How do I keep the backup up to date?**
Run `python kit.py close` from time to time. It checks which files changed in Figma since their backup. `python kit.py refresh` then moves their old copy to `temp/replaced/` and queues them; `python kit.py run` exports them again.

**How do I restore a file into Figma?**
Drag its `.fig` (or `.jam`, `.deck`) into Figma, or use Figma → Import.

**Why do some screens have a PDF instead of an SVG?**
Figma sometimes can't render a frame as SVG. The kit then asks for a vector PDF. A frame with neither is marked *empty frame* in the gallery.

**Why do some PNGs look smaller?**
Very tall frames are exported below @2x so Figma's renderer doesn't time out. The gallery shows the scale.

**Is my token safe?**
It stays in `workstation/.env` on your disk and is never printed or logged. See [Figma token](figma-token.md).
