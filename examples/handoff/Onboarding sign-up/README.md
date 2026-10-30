# Dev handoff: Onboarding

Pages: Screens · 5 frames · made 2026-10-30 13:16 by figma-offline-kit.
Fresh from Figma when it was made; the backup is a separate snapshot.

| Path | What |
|---|---|
| `index.html` | gallery of every frame; **Code & specs** opens the frame page |
| `frames/<frame>.html` | per frame: Design · Code · Tokens · Anatomy |
| `screens/png · svg · svg-tokens/` | images; token SVGs have colours as `var(--token, #hex)` |
| `code/<frame>.tsx` | Figma's design-to-code reference (React + Tailwind), assets in `code/assets/` |
| `components/<frame>.html` | anatomy of component frames: properties, variants, tokens, layers |
| `tokens/` | the design system's `tokens.css` / `_tokens.scss` (load `tokens.css` to run the code on your tokens) |
| `tokens-usage.json` · `components-usage.json` · `screens.json` | the data behind the pages |

## State

- screens: 5 frames, PNG + SVG
- tokens: 2 token SVGs, 2 frames with unbound colours
- code: 5 / 5 frames
- anatomy: 0 component pages
