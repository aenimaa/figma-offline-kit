# Figma token

The kit reads Figma through its REST API with a **personal access token**: a password-like key that belongs to your Figma account. The kit only reads; give the token read scopes only.

## Make one
1. In Figma (browser or desktop), click your avatar or the Figma menu → **Settings** → **Security** → **Personal access tokens** → **Generate new token**.
2. Name it, e.g. *figma-offline-kit*, and choose an expiry.
3. Tick these scopes, all **read**:

| Scope | Why the kit needs it |
|---|---|
| `current_user:read` | doctor checks the token works |
| `file_content:read` | pages, frames, layers, images |
| `file_metadata:read` | a file's project name when you give file links |
| `folders:read` (older pages: `projects:read`) | list a team's projects and their files |
| `file_variables:read` | *Enterprise plans only*: variables by REST. Without it, see [design tokens](tokens.md) |

4. Copy the token. Figma shows it once.

## Put it where the kit reads it
The token lives in one file inside your backup folder (the *workspace* you chose in the questions):

| | Default place |
|---|---|
| Windows | `C:\Users\<you>\figma-backup\workstation\.env` |
| macOS | `/Users/<you>/figma-backup/workstation/.env` |
| Linux | `~/figma-backup/workstation/.env` |
| Any workspace | `<workspace>/workstation/.env` |

The file is created by the setup questions. Its token line looks like this:

```
FIGMA_TOKEN=figd_your-token-here
```

**Easiest:** the guided start (`Start.bat`, `Start.command` or `python kit.py start`) prints the exact path and offers to
1. take the token right there, hidden (paste and press Enter; nothing shows while you paste), or
2. open the file in Notepad (Windows) or TextEdit (macOS), so you paste it after `FIGMA_TOKEN=` and save.

Then it checks the token with Figma before going on. `python kit.py init` in a terminal also offers the hidden prompt.

**In the download:** paste the token into **`Figma token.txt`** next to Start and save. Start moves it into `.env` and empties the txt again, so the token doesn't stay in your Downloads.

**By hand:** open the file in a plain text editor, paste the token after `FIGMA_TOKEN=`, save, then run `python kit.py doctor`. It should say *works (signed in as …)*. On macOS, Finder hides files whose names start with a dot: press Cmd+Shift+. to show them, or use the guided start.

You can use the environment variable `FIGMA_TOKEN` instead; it wins over the file.

## Keep it safe
- Don't paste the token in a chat with an AI. Paste it into the file yourself. If it ended up in a chat, make a new token and revoke the old one in the same Settings page.
- The token can only see files your account can see.
- `.env` is never part of the backup archives you share, and the kit never prints the token.
- When the backup is done, you can revoke the token.
