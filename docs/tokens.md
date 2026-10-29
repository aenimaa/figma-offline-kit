# Design tokens add-on

Two parts: the **variables** of your design-system file(s), and a **token report + token SVG** for every exported screen.

## 1 · Variables
| Source | How | Needs |
|---|---|---|
| REST | `python kit.py tokens vars` tries every design file | a Figma **Enterprise** plan (variables read scope on the token) |
| Figma MCP | the AI runs `templates/variables.js` with `use_figma` on the design-system file, saves the JSON it returns, then `python kit.py tokens import <file> <saved.json>` | Figma's MCP server connected to the AI |
| Native export | in Figma: Variables panel → right-click a collection → **Export modes** → save the zip; then `python kit.py tokens import <file> <zip>` | nothing; repeat per collection |

REST and MCP give the full data (ids, aliases, scopes, code syntax) in `variables/variables.figma.json`, plus `tokens.css` and `_tokens.scss`:
- names: the variable's **Web code syntax** if the designer set one (`var(--brand)` → `--brand`), else the slugged path (`color/bg` → `--color-bg`)
- default mode on `:root`, other modes on `[data-<collection>="<mode>"]`, aliases as `var(--other)`, sizes in px

The native export is kept as saved in `variables/figma-native/`. It has no variable ids, so it can't drive the token SVGs.

## 2 · Token report and token SVGs
`python kit.py tokens svgs` (add `--background` for big teams) goes through every exported file:
- `tokens-usage.json`: per screen, every variable and style used (by kind: colour, spacing, radius, type…), library variables resolved by key, and **unbound colours** (solid colours with no variable and no style).
- `screens/svg-tokens/…`: the screen's SVG with colours as `fill:var(--token, #hex)`. The hex stays as fallback, so it looks the same everywhere; inline it next to `tokens.css` to switch themes.
  - **raw**: no colour bound → the raw SVG is already the token SVG (no file)
  - **hex**: each bound colour's hex belongs to one token on that screen → rewritten by hex
  - **render**: a hex is shared (a token and a hard-coded colour) → Figma re-renders with layer ids and only bound layers are rewritten. Never a wrong token; at worst a hex stays.
- The gallery gets a **Raw SVG / Token SVG** switch and a **Tokens used** panel (T key).

**Library variables:** a screen that uses variables published from another file (a library) can only name them if that library file is in the backup too and its variables are saved. Until then the report lists them under `_unresolved` and `kit.py tokens` counts the screens.

Files changed in Figma since their backup are skipped: `python kit.py refresh` and `run` first.
