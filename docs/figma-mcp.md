# Figma MCP servers

MCP is the way AI assistants talk to other apps. Figma has two MCP servers, and the kit can use each for one optional job. Neither is needed for the backup itself.

| | Figma's MCP server (remote) | Figma desktop's MCP server (local) |
|---|---|---|
| Where | connected to **your AI app** (Claude, Cursor, VS Code…) | runs inside **Figma desktop** at `http://127.0.0.1:3845/mcp` |
| Used for | reading **variables** without an Enterprise plan (`use_figma`) | **dev handoff code**: Figma's design-to-code per frame |
| Who calls it | your AI | the kit itself |
| Check | your AI tells doctor: `kit.py doctor --ai figma-mcp=yes` | doctor: *Figma desktop MCP* row |

## Remote: variables through your AI
1. Connect Figma's MCP server in your AI app (its settings → connectors or MCP; sign in to Figma there).
2. The AI runs `python kit.py tokens script`, executes that code on your design-system file with `use_figma` (read-only), saves the JSON it returns, and runs `python kit.py tokens import <file> <saved.json>`.

The code only reads variables: collections, modes, values, aliases, scopes and code syntax.

## Local: code for the dev handoff
1. Open Figma desktop and the file you hand off.
2. Turn on the local MCP server. Figma moves this switch between versions: look in the Figma menu → **Preferences**, or in **Dev Mode** (Shift+D) → the inspect panel's MCP section. Some versions only offer remote clients; then the handoff skips the code step and does everything else.
3. `python kit.py doctor` shows whether it answers, then run `python kit.py handoff …` again: only the missing code is filled in.

After Figma restarts, open the handed-off page once before running, or design-to-code may hang.
