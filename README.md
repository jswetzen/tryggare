# Handoff: Tryggare landing page

## Overview
**Tryggare** (Swedish for *"safer"*) is a self-hosted child check-in system for churches and organizations. This handoff covers its **public marketing landing page** — a single-page static site with a bilingual (English / Swedish) toggle, deployed to GitHub Pages at the `gh-pages` branch of `jswetzen/tryggare`.

The page introduces the product, lists features, makes the self-hosted / data-ownership pitch, and drives visitors to the GitHub repo and a live demo.

## Context: what changed in this handoff
The latest design lives in `index.html` (this bundle). It was reconciled with two **manual commits** that had been made directly on the deployed `gh-pages` branch, so the design source and the live site now match:

1. **Wordmark simplified** — `Tryggare.app` → **`Tryggare`** everywhere (nav brand, footer brand, `<title>`, and the JS that swaps the document title per language). The `.tld` accent span was removed.
2. **Phone screenshot swapped** — the hero phone mockup now uses `uploads/checkin_screenshot.png` (a clean check-in screen) instead of the earlier `Screenshot_20260429-122431_Firefox.png`.

Everything else in `index.html` (live-demo CTA, demo note, EN/SV i18n, all sections) is the newer design and should be kept.

## About the Design Files
Unlike most design handoffs, the file in this bundle is **not just a reference mock — it is the actual production artifact.** `index.html` is a self-contained, vanilla HTML/CSS/JS page (no build step, no framework, no dependencies beyond a Google Fonts link). It is what gets deployed to GitHub Pages.

You therefore have two reasonable paths:
- **Maintain as-is (recommended for this project):** keep it as a single static `index.html` and deploy to `gh-pages`. It's intentionally dependency-free and trivially hostable. This is how it's deployed today.
- **Port into a framework** (only if the wider product site moves to one): recreate the markup/styles in the target environment (React/Astro/etc.) using its conventions. The design tokens and section specs below give you everything needed.

## Fidelity
**High-fidelity (hifi) and final.** Exact colors (OKLCH), typography (Plus Jakarta Sans), spacing, radii, shadows, and interactions are all specified in the source and reproduced below. Treat measurements as authoritative.

## Tech at a glance
- **Single file:** `index.html` — inline `<style>` and inline `<script>`, no external JS/CSS.
- **Font:** Plus Jakarta Sans via Google Fonts (`400;500;600;700;800`).
- **i18n:** runtime English/Swedish toggle. Strings live in a JS dictionary keyed by `data-i18n` attributes; selection persists in `localStorage`. The `<html lang>` and `document.title` update on switch.
- **No router, no state library, no analytics, no cookies.**
- `colors_and_type.css` is the **canonical design-token reference** (a superset of the tokens inlined in `index.html`). It is NOT linked by the page — it documents the system. If you port to a framework, lift tokens from here.

## Screens / Views
The page is one continuous scroll. Sections in order:

### 1. Nav (sticky)
- **Layout:** sticky top bar, `height: 64px`, flex space-between, horizontal padding `clamp(20px, 5vw, 80px)`. Glassy background `oklch(0.99 0.004 240 / 0.88)` with `backdrop-filter: blur(14px)` and a 1px bottom border `oklch(0.88 0.006 240)`.
- **Left:** brand — logo SVG + wordmark **"Tryggare"**, `1.2rem / 700`, letter-spacing `-0.02em`.
- **Right:** language switcher (globe icon + `EN`/`SV` label + chevron, opens a dropdown with English / Svenska and a ✓ on the active one), a ghost "View on GitHub" link, and a primary CTA button.

### 2. Hero
- **Layout:** centered container `max-width: 1300px`. Two-column grid `1fr 1fr`, `gap: 60px`, vertical padding `clamp(60px, 9vw, 120px)`. Collapses to one column on narrow viewports.
- **Left (text):**
  - Eyebrow badge — pill, green tint bg `var(--green-light)`, green text, uppercase `0.78rem / 700`, with a 6px green status dot.
  - `h1` — `clamp(2.4rem, 4.5vw, 3.6rem)`, weight `800`, line-height `1.1`, letter-spacing `-0.03em`, `text-wrap: balance`. Emphasis words use `<em>` rendered in `var(--blue)` (not italic).
  - Sub — `1.1rem`, `var(--ink-soft)`, max-width `480px`.
  - CTA row — primary + outline buttons, plus a small demo note line.
- **Right (visual):** a phone mockup framing **`uploads/checkin_screenshot.png`** (alt: "Tryggare check-in screen showing family list with check-in status").

### 3. Features (`#features`)
- Centered container `max-width: 1140px`.
- Section label eyebrow, `h2` "Everything a busy Sunday needs", sub paragraph, then a grid of feature cards (icon + title + body).

### 4. Self-hosted pitch (`#self-hosted`)
- Two-part section: label + `h2` "Your data stays yours" with a checklist (`.pitch-list`) making the data-ownership / no-per-child-fees argument. Danger-tinted ✗ rows use `--danger` tokens.

### 5. Open Source CTA (`.oss-section`)
- Label "Open Source", `h2` "Built in the open, for everyone", sub explaining AGPL-3.0 licensing and that PRs/issues are welcome, plus repo CTA(s).

### 6. Footer
- Brand wordmark **"Tryggare"** + footer links.

## Interactions & Behavior
- **Buttons:** `.btn` base — inline-flex, `gap: 7px`, `padding: 9px 18px`, `border-radius: 8px`, `0.875rem / 600`, `transition: all 0.15s ease`.
  - `.btn-primary` — `var(--blue)` bg, white text; hover → `var(--blue-mid)`, `translateY(-1px)`, shadow `0 4px 16px oklch(0.52 0.20 232 / 0.30)`.
  - `.btn-ghost` — transparent; hover → `var(--surface-2)` bg, `var(--ink)` text.
  - `.btn-outline` — transparent, `1.5px` border `oklch(0.80 0.08 232)`, `var(--blue)` text; hover → `var(--blue-light)` bg.
  - `.btn-lg` — `padding: 14px 28px`, `1rem`, `border-radius: 10px`.
- **Language switcher:** `toggleLangMenu()` opens/closes the dropdown; `setLang('en'|'sv')` swaps all `data-i18n` text, updates `#lang-label`, the active ✓, `<html lang>`, and `document.title`; choice persists in `localStorage`. Clicking outside closes the menu.
- **Smooth scrolling:** `html { scroll-behavior: smooth; }` for in-page anchor nav.
- **Responsive:** hero grid and other multi-column sections collapse to single column at small widths via the existing media queries in `index.html`.

## State Management
Minimal, all client-side:
- **`lang`** — `'en' | 'sv'`, read from `localStorage` on load (default `'en'`), written on every switch. Drives all visible copy, `#lang-label`, the active language ✓, `<html lang>`, and `document.title`.
- **Lang menu open/closed** — transient UI flag in the DOM (dropdown visibility class).
No data fetching, no server calls.

## Design Tokens
Canonical source: **`colors_and_type.css`** (bundled). Key values:

**Color (OKLCH):**
- `--blue` / `--brand-primary` `oklch(0.56 0.22 265)` (~#3B82F6) · `--blue-mid` `oklch(0.48 0.23 265)` · `--blue-light` `oklch(0.95 0.04 265)`
- `--green` / `--brand-accent` `oklch(0.60 0.17 145)` (~#22C55E) · `--green-light` `oklch(0.95 0.06 145)`
- `--ink` `oklch(0.14 0.015 240)` · `--ink-soft` `oklch(0.40 0.010 240)` · `--ink-faint` `oklch(0.60 0.008 240)`
- `--surface` `oklch(0.99 0.004 240)` · `--surface-2` `oklch(0.96 0.006 240)` · glass `oklch(0.99 0.004 240 / 0.88)`
- `--danger` `oklch(0.50 0.14 18)` · `--danger-tint` `oklch(0.93 0.015 18)`

**Radius:** `--radius-sm 7px` · `--radius 10px` (`14px` inline as `--radius`) · `--radius-md 14px` · `--radius-lg 22px` · pill `100px`. (Note: `index.html` inlines `--radius: 14px` / `--radius-lg: 22px`; `colors_and_type.css` is the fuller scale.)

**Shadow:** `--shadow-xs 0 2px 8px oklch(0.14 0.015 240 / 0.07)` · `--shadow-sm 0 4px 16px /0.08` · `--shadow-md 0 8px 28px /0.14` · `--shadow-lg 0 40px 80px /0.22, 0 12px 24px /0.10` · `--shadow-cta 0 4px 16px oklch(0.52 0.20 232 / 0.30)`.

**Motion:** `--motion-fast 0.12s` · `--motion-base 0.15s ease` · `--motion-slow 0.20s ease`.

**Typography:** `--font-sans 'Plus Jakarta Sans', -apple-system, …`. Ramp: display `clamp(2.4rem,4.5vw,3.6rem)` · h2 `clamp(1.8rem,3vw,2.6rem)` · h3 `1rem` · body-lg `1.1rem` · body `1rem` · body-sm `0.875rem` · caption `0.8rem` · eyebrow `0.78rem`. Weights shipped: 400/500/600/700/800.

**Spacing scale:** 4 · 8 · 12 · 16 · 20 · 28 · 36 · 44 · 60 · 80 · 120 (px), as `--space-1` … `--space-11`.

## Assets
- **`uploads/checkin_screenshot.png`** — hero phone screenshot (the live check-in screen). This is the image introduced by the manual gh-pages commit; bundled here. Required.
- **Logo** — inline SVG in the nav and footer brand marks (gradient stops defined in `colors_and_type.css`: `--logo-sweep-start #3B82F6` → `--logo-sweep-end #1E40AF`, `--logo-accent-start #22C55E` → `--logo-accent-end #15803D`).
- **Plus Jakarta Sans** — loaded from Google Fonts (external CDN link in `<head>`).
- No icon library — all icons are inline SVG.

## Deployment
Static GitHub Pages site. To publish: commit `index.html` (and the `uploads/` image) to the **`gh-pages`** branch of `jswetzen/tryggare`; Pages serves it at the repo's Pages URL. No build step.

## Files in this bundle
- **`index.html`** — the complete, production landing page (reconciled with the gh-pages manual edits). Inline CSS + JS.
- **`uploads/checkin_screenshot.png`** — hero screenshot asset referenced by `index.html`.
- **`colors_and_type.css`** — canonical design-token reference (documentation; not linked by the page).
- **`README.md`** — this document.
