# Tryggare design system

The brand layer shared between the **app** (this repo's SvelteKit frontend) and the
**marketing site** (`gh-pages` branch, `tryggare.app`). Palette is sky blue + green,
typeface is Plus Jakarta Sans, wordmark is **"Tryggare"** (no `.app`, never translated).

## Where things live

| Thing | Location | Notes |
|-------|----------|-------|
| **Canonical tokens** | `frontend/src/lib/styles/tokens.css` | Single source of truth for colors / radii / shadows / type. Imported globally in `+layout.svelte`. |
| Tailwind mirror | `frontend/tailwind.config.cjs` | Brand values mirrored so utilities (`bg-primary-600`, `shadow-cta`, …) resolve to the brand. Annotated with `// --token`. |
| Drift guard | `frontend/scripts/check-design-tokens.mjs` | `npm run check:tokens` — fails if the mirror drifts from `tokens.css`. Runs in CI. |
| Brand primitives | `frontend/src/lib/components/ui/` | `Logo.svelte`, `Wordmark.svelte` (more to follow — see HANDOFF.md). |
| Brand guide | `DESIGN_SYSTEM.md` | Full visual + content language (tone, palette, type, motion, iconography). |
| Integration brief | `HANDOFF.md` | The original design-team handoff this work is derived from. |
| Sharing strategy | `SHARING.md` | How the app and marketing site share the token layer without drift. |
| UI-kit specs | `ui-kit-reference/*.jsx` | **Reference only — not shipped.** Visual specs (measurements, hover states) for porting primitives to Svelte. |
| Assets | `assets/` | Canonical 2-path logo (`logo-current.svg`), original artist file, hero screenshot. |

## Working rules (summary)

These are enforced as standing guidance in the repo root `CLAUDE.md`. In short:

- Never hard-code colors / radii / shadows. Use the Tailwind semantic classes
  (`primary` / `success` / `neutral` / …) or the `var(--…)` tokens.
- Palette is **sky blue + green**. Green (`success` / `--brand-accent`) is reserved for the
  trust / success / "live" signal — don't spread it around decoratively.
- Wordmark is **"Tryggare"** — no `.app`, not translated.
- **Bilingual by default** — every visible string gets EN + SV in the same change.
- **No emoji.** Allowed glyphs: ✓ ✗ →. Icons are stroke-only (Lucide), width 2, `currentColor`.
- **Plus Jakarta Sans** only. Restrained motion (`0.15s ease`, 1–2px hover lifts).

See `DESIGN_SYSTEM.md` for the full rationale.
