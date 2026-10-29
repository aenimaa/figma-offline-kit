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
After `python kit.py init`, open `<workspace>/workstation/.env` in a text editor and paste the token after `FIGMA_TOKEN=`:

```
FIGMA_TOKEN=figd_your-token-here
```

Save, then run `python kit.py doctor`. It should say *works (signed in as …)*. Running `init` in a terminal also offers a hidden prompt to paste it.

You can use the environment variable `FIGMA_TOKEN` instead; it wins over the file.

## Keep it safe
- Don't paste the token in a chat with an AI. Paste it into the file yourself. If it ended up in a chat, make a new token and revoke the old one in the same Settings page.
- The token can only see files your account can see.
- `.env` is never part of the backup archives you share, and the kit never prints the token.
- When the backup is done, you can revoke the token.
