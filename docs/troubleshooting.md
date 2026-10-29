# Troubleshooting

Start with `python kit.py doctor` and `python kit.py status`: most problems show up there. The run's log is `workstation/logs/run.log`.

| What you see | What to do |
|---|---|
| **Figma token: no Figma token found** | paste it into `workstation/.env` after `FIGMA_TOKEN=` ([how](figma-token.md)) |
| **Figma refused the token (403)** | the token expired, was revoked, or lacks a scope. Make a new one with the scopes in [Figma token](figma-token.md) |
| **can't read team … (404 or 403)** | check the team link, that your account is a member, and the `folders:read` scope. Or back up single files: paste file links in the interview |
| **api.figma.com not reachable** | check the internet, VPN or proxy. A running export waits on its own and continues the same file |
| **rate limit … waiting Ns** | normal. Figma asked the kit to slow down; it waits the full time Figma asks |
| **Phase: running (process gone)** | the computer slept or restarted: `python kit.py resume` |
| **a file shows ✖ in the run report** | `python kit.py resume` retries failed files. If it fails again, the error is in `run.log` |
| **"Confirm the pages to back up first"** | `python kit.py pages`, then `python kit.py pages --confirm` |
| **The gallery opens blank in a browser** | some browsers block `file://` pages: `python -m http.server --directory "<workspace>/backup"` and open the address it prints |
| **Local copy: "wait N s" or "daily limit"** | pacing against Figma's bot checks (≈ 40 a day, 60 s apart). Continue later |
| **Figma shows "verify you are not a bot"** | a person must complete it. Then continue more slowly, or tomorrow |
| **Local copy saved but not ticked off** | `python kit.py copies check`. It looks in the target folder, `temp/incoming` and Downloads; the file name must match the Figma file name |
| **Local copy marked failed** | the saved file is empty or not a Figma file (for example a partial save). Delete it and save again |
| **tokens: "use library variables not in the backup"** | the screens use variables published from another file. Add that file to the backup and import its variables |
| **handoff: code skipped** | Figma desktop's local MCP server isn't answering ([Figma MCP](figma-mcp.md)). Everything else in the handoff is done; run the command again later |
| **Windows: strange characters in the console** | the kit sets UTF-8 itself; if you pipe its output in PowerShell 5, write to a file from Python instead |
| **Path too long (Windows)** | the kit uses long-path names; if another tool fails on them, choose a shorter workspace folder, e.g. `D:\fb` |
