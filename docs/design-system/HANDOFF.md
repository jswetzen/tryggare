# Handoff: integrate the Tryggare design system into the app

## Overview

The marketing landing page (`tryggare.app`) and the check-in app (SvelteKit, `github.com/jswetzen/check-ins`) currently **look similar but share nothing**. The app re-declares its own colors, spacing, and component styles by hand. The result is *drift*: every time the design system changes, the app falls a little further out of sync.

The goal of this handoff is **closer integration** — not a new feature. Concretely: make the design system a set of files the app **imports and consumes**, so that "matching the brand" stops being a manual copy job and becomes structural.

This package is the brief for doing that work in Claude Code, inside the SvelteKit repo.

## About the design files

The files in `ui-kit-reference/` are **React/JSX design references** — they show the intended look and behavior of each primitive. They are **not** meant to be shipped. The check-in app is **SvelteKit**, so the task is to **recreate these primitives as Svelte components** in the app's existing environment, each consuming the shared CSS tokens. Treat the JSX as a precise spec (measurements, colors, hover states), not as code to port line-for-line.

The files in `design-system/` — especially `colors_and_type.css` — **are** meant to ship. That CSS file should become the single source of truth the app imports.

## Fidelity

**High-fidelity.** Every value below is final: exact tokens, exact paddings, exact hover transforms. Recreate the primitives pixel-for-pixel using Svelte + the shared CSS variables. Where the app already has a working component (e.g. a button), refactor it to consume the tokens rather than introducing a parallel one.

---

## The integration strategy (do these in order)

### 1. Make `colors_and_type.css` the single source of truth

This is the highest-impact step and unblocks everything else.

1. Copy `design-system/colors_and_type.css` into the app, e.g. `src/lib/styles/tokens.css`.
2. Import it **once**, globally — in `src/routes/+layout.svelte` (`<style>@import …</style>` or an import in `src/app.css` that's already linked by `app.html`). After this, every `--brand-primary`, `--radius-lg`, `--shadow-md`, `--type-display`, etc. is available app-wide.
3. **Delete the app's hand-rolled color/spacing values** and replace them with the corresponding `var(--…)`. Search the codebase for hex literals (`#3B82F6`, `#22C55E`, `#1E40AF`, `#15803D`), `oklch(` declarations, and ad-hoc `border-radius` / `box-shadow` values; swap each for the matching token. The token file already ships **legacy shorthands** (`--blue`, `--green`, `--blue-light`, …) so older markup keeps working during the transition.
4. **Sync mechanism — pick one** so this file never diverges again:
   - *Copy + CI guard (simplest):* keep the canonical file in the design-system project; copy it into the app; add a CI step that fails if the two differ (a checksum comparison). Cheap, no publishing.
   - *npm workspace / package:* publish the design system as `@tryggare/tokens`; the app depends on it and imports `@tryggare/tokens/tokens.css`. Cleaner, more setup.
   - *git submodule:* vendor the design-system repo into the app under `design-system/`. Good if you want the docs and assets alongside the tokens.
   - **Recommendation:** start with *copy + CI guard*. It gives you the no-drift guarantee today with near-zero infrastructure, and you can graduate to a package later.

### 2. Port the UI kit to Svelte primitives

Build a small `src/lib/components/` set that mirrors the kit. Each component **reads tokens — it ships no hex of its own** (same rule the JSX follows). Specs are in the "Component specs" section below. Minimum set, in priority order:

1. `Button.svelte` — the most reused primitive; do this first.
2. `Logo.svelte` + `Wordmark.svelte` — needed in the app shell / nav.
3. `Pill.svelte`, `StatusBadge.svelte`, `EyebrowLabel.svelte`.
4. `FeatureCard.svelte`, `ComparisonRow.svelte` — lower priority (more marketing-shaped, but useful for in-app empty states and settings rows).

Once these exist, refactor existing app screens to use them instead of bespoke markup. That's where the "closer integration" becomes visible.

### 3. Give Claude Code the design system as a standing skill in the app repo

So future UI work in the app auto-respects the brand:

1. Drop `CLAUDE_for_app_repo.md` (in this bundle) into the **app repo root as `CLAUDE.md`** — it's pre-written with the working rules, token names, and voice guardrails.
2. Optionally also vendor `design-system/` (or reference the package) so the agent can read `DESIGN_SYSTEM.md` + `colors_and_type.css` directly.

After this, an instruction like "add a settings page" produces on-brand output without re-stating the rules each time.

---

## Component specs

All values are taken verbatim from the production JSX in `ui-kit-reference/`. Every color is a token from `colors_and_type.css`.

### Button (`Button.svelte`)
- **Props:** `variant` (`primary` | `outline` | `ghost` | `white` | `outlineWhite`, default `primary`), `size` (`md` | `lg`, default `md`), `href` (renders `<a>` when set, else `<button>`).
- **Base:** `display: inline-flex; align-items: center; gap: 7px; font-family: inherit; font-weight: 600; text-decoration: none; cursor: pointer; border: none; white-space: nowrap; transition: all 0.15s ease;`
- **Sizes:** `md` → `padding: 9px 18px; font-size: 0.875rem; border-radius: 8px`. `lg` → `padding: 14px 28px; font-size: 1rem; border-radius: 10px`.
- **Variants (rest → hover):**
  - `primary`: bg `var(--brand-primary)`, color `#fff` → bg `var(--brand-primary-mid)`, `translateY(-1px)`, `box-shadow: var(--shadow-cta)`.
  - `outline`: transparent, color `var(--brand-primary)`, `border: 1.5px solid oklch(0.80 0.08 232)` → bg `var(--brand-primary-tint)`.
  - `ghost`: transparent, color `var(--ink-soft)` → bg `var(--surface-2)`, color `var(--ink)`.
  - `white`: bg `#fff`, color `var(--ink)` → bg `var(--surface-2)`, `translateY(-1px)`.
  - `outlineWhite`: transparent, color `#fff`, `border: 1.5px solid oklch(0.35 0.010 240)` → bg `oklch(0.20 0.010 240)`.
- External `href` (starts with `http`) gets `target="_blank" rel="noopener"`.
- **GitHubMark** is the one filled icon allowed — a 24×24 `fill="currentColor"` octocat, used inside "View on GitHub" buttons.

### Logo (`Logo.svelte`) + Wordmark (`Wordmark.svelte`)
- **Logo:** two-path SVG, `viewBox="0 0 256 256"`, default `size=34`. Two `linearGradient`s with `gradientUnits="userSpaceOnUse"`; stops driven by `--logo-sweep-start/end` and `--logo-accent-start/end`. **Give each instance a unique gradient `id`** (prop) so multiple logos on one page don't collide. Copy the two `<path d="…">` strings verbatim from `ui-kit-reference/Logo.jsx` (or `design-system/assets/logo-current.svg`).
- **Wordmark:** `font-weight: 700; letter-spacing: -0.02em; color: var(--ink)`. Prop `showTld` — **default `false`** in the app (canonical "Tryggare" alone; the `.app` domain is provisional). When shown, `.app` is colored `var(--brand-primary)`.

### EyebrowLabel / Pill / StatusBadge (`Pill.svelte`)
- **EyebrowLabel:** flex row, `gap: 8px`; a 20×2px dash (`background: color; border-radius: 2px`) then text at `0.78rem / 700 / letter-spacing 0.08em / uppercase`, color default `var(--brand-primary)`, `margin-bottom: 16px`.
- **Pill:** inline-flex, `gap: 6px`, bg `var(--brand-accent-tint)`, color `var(--brand-accent)`, `0.78rem / 700 / 0.06em / uppercase`, `padding: 5px 12px; border-radius: 100px`. Optional leading 6×6 dot in `var(--brand-accent)`.
- **StatusBadge:** white pill, `border-radius: 12px; padding: 10px 14px; box-shadow: var(--shadow-md)`; a 28×28 rounded-8 tile (`var(--brand-accent-tint)` bg, `var(--brand-accent)` icon) holding a ✓, then `0.8rem / 600` text.

### FeatureCard (`FeatureCard.svelte`)
- Card: bg `var(--surface)`, `border: 1px solid var(--ink-line)`, `border-radius: var(--radius-lg)`, `padding: 28px 28px 24px`.
- Hover: `box-shadow: var(--shadow-sm)` + `transform: translateY(-2px)`, transition `box-shadow 0.2s ease, transform 0.2s ease`.
- Icon tile: 44×44, `border-radius: 11px`, `margin-bottom: 18px`. Tone `blue` → bg `var(--brand-primary-tint)` / color `var(--brand-primary)`; tone `green` → `var(--brand-accent-tint)` / `var(--brand-accent)`.
- Title: `1rem / 700 / letter-spacing -0.01em`. Body: `0.875rem`, `var(--ink-soft)`, `line-height: 1.55`.

### ComparisonRow (`ComparisonRow.svelte`)
- Row: white, `border-radius: 10px; padding: 14px 18px; box-shadow: var(--shadow-xs)`, flex `gap: 14px`.
- Status disc: 26×26 circle, `font-size: 0.75rem`. `yes` → bg `var(--brand-accent-tint)`, color `var(--brand-accent)`, glyph ✓. `no` → bg `var(--danger-tint)`, color `var(--danger)`, glyph ✗.
- Title: `0.875rem / 600` (`var(--ink)` when yes, `var(--ink-soft)` when no). Sub: `0.78rem`, `var(--ink-faint)`.

### LangSwitcher (`LangSwitcher.svelte`)
- Globe-glyph toggle button + dropdown. The **app likely already has i18n** (the production page uses a `T = { en, sv }` block + `data-i18n`). Wire this component to the app's existing locale store rather than introducing a second source of language state.
- Trigger: `padding: 6px 10px; border-radius: 7px; 0.8rem / 600`; rest color `var(--ink-soft)`, open state bg `var(--surface-2)` / color `var(--ink)`. Globe SVG is stroke-only, width 2, `opacity 0.7`; chevron rotates on open.
- Menu: white, `border-radius: 9px`, `box-shadow: 0 4px 20px oklch(0.14 0.015 240 / 0.14), 0 0 0 1px var(--ink-line)`, `min-width: 140px`. Active locale shows a `var(--brand-accent)` ✓ at the row end. Closes on outside-click.

---

## Design tokens (reference)

The full set lives in `design-system/colors_and_type.css`. **Always reference via `var(--…)` — never hard-code.** Key groups:

- **Brand:** `--brand-primary` `oklch(0.56 0.22 265)` (#3B82F6), `--brand-primary-mid`, `--brand-primary-tint`; `--brand-accent` `oklch(0.60 0.17 145)` (#22C55E), `--brand-accent-mid`, `--brand-accent-tint`.
- **Logo gradient stops:** `--logo-sweep-start` #3B82F6 → `--logo-sweep-end` #1E40AF; `--logo-accent-start` #22C55E → `--logo-accent-end` #15803D.
- **Neutrals:** `--ink`, `--ink-soft`, `--ink-faint`, `--ink-line`, `--ink-line-2`, `--surface`, `--surface-2`, `--surface-glass`; danger `--danger-tint` / `--danger`.
- **Radii:** `--radius-sm` 7 · `--radius` 10 · `--radius-md` 14 · `--radius-lg` 22 · `--radius-pill` 100.
- **Shadows:** `--shadow-xs` / `-sm` / `-md` / `-lg` / `-cta` (all cool, ink-toned).
- **Type:** font `Plus Jakarta Sans` (400/500/600/700/800); fluid ramp `--type-display` → `--type-eyebrow`; weight tokens `--weight-regular … --weight-black`. Semantic classes `.display .h2 .h3 .body-lg .body .body-sm .caption .eyebrow` are defined in the file — reuse them.
- **Spacing:** `--space-1` (4px) … `--space-11` (120px).

---

## Content & behavior rules (carry into the app UI)

- **Voice:** warm, practical, low-key technical. Second-person ("your data"), never "we/our". Refer to the product by name ("Tryggare is…").
- **Casing:** sentence case everywhere — headlines, buttons, labels. Eyebrows are UPPERCASE letter-spaced as a device only.
- **Bilingual by default:** every visible string needs EN + SV; Swedish conveys intent, not literal words. Add both in the same change.
- **No emoji.** Allowed glyphs only: ✓ ✗ →. Context is children's safety — calm seriousness.
- **Iconography:** inline SVG, stroke-only, width 2, `currentColor`, rounded caps/joins. Use Lucide as the substitute set. Octocat is the one filled exception.
- **Gradients:** none except the logo's two and the self-hosted panel (135°, `--brand-primary-tint` → `--brand-accent-tint`). **No purple-to-blue / AI mesh gradients.**
- **Motion:** restrained — `0.15s ease` base, 1–2px hover lifts, no springs/bounces.

---

## Files in this bundle

```
README.md                         ← this guide
CLAUDE_for_app_repo.md            ← drop into the app repo root as CLAUDE.md
design-system/
  colors_and_type.css             ← SHIP THIS — the single source of truth
  DESIGN_SYSTEM.md                ← full brand + visual reference (was the DS README)
  SKILL.md                        ← agent entry-point for the design system
  assets/
    logo-current.svg              ← canonical 2-path logo (gradients as hex)
    logo.svg                      ← original artist file
    checkin-screen.png            ← hero screenshot
ui-kit-reference/                 ← React/JSX SPECS (do not ship — port to Svelte)
  Button.jsx  Logo.jsx  Pill.jsx  FeatureCard.jsx  ComparisonRow.jsx  LangSwitcher.jsx
```

## Suggested first PR

A tight, reviewable starting slice that proves the pipeline end-to-end:
1. Add `tokens.css` and import it globally in `+layout.svelte`.
2. Replace every hard-coded brand hex / radius / shadow in the app with the matching token.
3. Ship `Button.svelte` (consuming tokens) and refactor existing buttons to use it.
4. Add `CLAUDE.md` to the repo.

That single PR removes the largest source of drift and sets the pattern for the rest of the kit.
