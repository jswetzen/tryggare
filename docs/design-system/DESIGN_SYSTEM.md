# Tryggare — design system

**Tryggare** (Swedish for *"safer"*) is a self-hosted child check-in system for churches and organizations. It's open-source (AGPL-3.0), runs on a church's own server, handles multi-station check-in over a local network, prints Brother QL labels, and supports both English and Swedish.

> **Naming.** The product is currently just **"Tryggare"**. The marketing site uses **"tryggare.app"** as a visual treatment, but the `.app` domain isn't owned yet — so the `.app` suffix should be considered **provisional**. When the brand wordmark is used in serious contexts (favicons, app installs, README, GitHub), drop the suffix and show **"Tryggare"** alone.

This design system documents the visual + content language of the marketing landing page (`index.html`) so it can be extended consistently to docs, the app shell, and any future surfaces.

## Sources

- `index.html` — the production landing page. Source of truth for tokens.
- `logo-colors.html` — the exploration that led to the current sky-blue + green palette. Kept around as reference, not active design.
- `assets/logo-current.svg` — the production logo (sweep + accent paths, two gradients).
- `uploads/Screenshot_20260429-122431_Firefox.png` — a screenshot of the check-in screen used as the hero phone image.
- GitHub repo: <https://github.com/jswetzen/check-ins> (Django + SvelteKit + PostgreSQL).

---

## Content fundamentals

**Tone.** Warm, practical, low-key technical. Written *to* church volunteers and small-org admins, not at them. No hype, no superlatives, no "revolutionary." Sentences are short. Hyphens and em-dashes carry the rhythm.

**Voice.** Second-person for the reader ("your data", "you need"); never first-person ("we", "our"). The product is referred to by name — "Tryggare is free and open-source", not "we are free and open-source".

**Casing.** Sentence case everywhere — headlines, buttons, labels. Eyebrow labels are **UPPERCASE** with letter-spacing, but only as a typographic device. Never Title Case A Sentence Like This.

**Punctuation.** Em-dashes ( — ) for asides. The Swedish copy keeps the same em-dash rhythm. Lists in copy use the serial comma. Arrows are real characters (`→`), not glyph fonts.

**Bilingual.** Every visible string lives in the `T = { en, sv }` block at the bottom of `index.html` and is referenced via `data-i18n` / `data-i18nh`. **When you add copy, add both languages in the same change.** Swedish should sound native — translate the *intent*, not the words ("Skip the Sunday-morning queue" → "Slipp söndagsmorgonens kö", not a literal rendering).

**No emoji.** The product is for a serious context (children's safety). The only "glyphs" in the design are ✓ and ✗ inside the self-hosted comparison rows, and the `→` in "Read the deploy guide →". No icons that imply playfulness.

**Stat formatting.** Concrete and unhyped — "$0/child", "$0/month", "Stations in parallel". The Swedish equivalent uses "0 kr/barn", "0 kr/månad". Never inflate ("100% free!") — the calmness is the message.

**Example phrases that capture the voice:**
- *"Everything a busy Sunday needs."*
- *"Designed for the reality of church life."*
- *"Your data stays yours."*
- *"Built in the open, for everyone."*
- *"No internet required on check-in day."*

---

## Visual foundations

### Palette
The system is **two-color**: a primary (sky blue, `#3B82F6`) and an accent (green, `#22C55E`). The accent is used sparingly — almost exclusively for the "trust / live / yes" signal (the badge dot, the ✓ row, the second logo gradient, the active language check mark). Everything else uses the primary blue or the neutral ink scale.

Backgrounds are near-white (`oklch(0.99 0.004 240)` — a 0.4%-chroma cool white). Section alternation uses a barely-tinted `surface-2`. There is exactly one dark section in the whole page (the OSS CTA), which uses `--ink` as the background and inverts the eyebrow color to green.

Gradients are **rare and intentional**. The only gradient surface is the `selfhosted-visual` panel, which fades from `--blue-light` to `--green-light` at 135°. The logo itself contains two linear gradients (sweep + accent paths). **Do not introduce purple-to-blue gradients or "AI-style" mesh gradients** — they are off-brand.

### Type
**Plus Jakarta Sans** is the only typeface, loaded from Google Fonts at weights 400 / 500 / 600 / 700 / 800. Headlines use 800 (`--weight-black`), body 400, UI labels 600–700. Letter-spacing is tightened on big headlines (`-0.03em` at the display size) and loosened on eyebrow labels (`0.08em`).

Line-height: `1.6` for body, `1.1` for display, `1.55` for body-small inside cards. `text-wrap: balance` on headlines, `text-wrap: pretty` on long body paragraphs.

### Spacing & layout
Page sections use **fluid padding** with `clamp(60px, 8vw, 100px)` so the rhythm survives any viewport. Horizontal padding uses `clamp(20px, 5vw, 80px)`. Content max-widths: `1300px` for hero / self-hosted, `1140px` for the features grid. Grids are bold and symmetrical — `1fr 1fr` for hero, `repeat(3, 1fr)` for features, collapsing to 2 then 1 at `900px` and `600px`.

### Cards, borders, radii
- Cards: `--radius-lg` (22px), 1px solid `--ink-line` border, no shadow at rest. Hover adds a soft `--shadow-sm` and a 2px `translateY` lift.
- Buttons: 8px–10px radius depending on size. Primary buttons lift 1px on hover and gain a colored shadow tinted with the primary.
- Pills (badges): `100px` radius, tinted background + matching text color.
- The phone mockup uses a 42px outer radius with a 32px inner screen radius — a real iOS proportion.

### Shadows
Three-tier system, all using `oklch(0.14 0.015 240 / α)` so the shadow stays cool and ink-toned, never gray-muddy:
- `--shadow-xs` for small UI surfaces (sh-row).
- `--shadow-sm` for card hover.
- `--shadow-md` for the floating "Checked in" badge.
- `--shadow-lg` (double-layer) for the phone mockup.
- `--shadow-cta` is the special colored hover-shadow on primary buttons.

### Motion
Restrained. Standard interaction transition is `0.15s ease`. Hover on primary buttons combines `transform: translateY(-1px)` + colored shadow. Cards lift `2px`. No spring physics, no bounces, no decorative micro-animations. The sticky nav uses `backdrop-filter: blur(14px)` for the glass effect — that is the showiest CSS the page contains.

### Imagery
One photographic asset: a real screenshot of the check-in app inside an iPhone-style frame. No stock photography, no illustrations, no icons-as-mascots. If a new image is needed, it should be a real screenshot or a real product photo — never a generated illustration.

### Iconography
**Inline SVG, stroke-only, currentColor.** Stroke width `2`, `stroke-linecap="round"`, `stroke-linejoin="round"`. The set is hand-rolled (drawn into the markup directly) and visually consistent with Lucide / Feather. Sizes are 16, 18, or 22px in the marketing page. **Use Lucide as the substitute set** when reaching for an icon that isn't in the page already — it matches the existing stroke style exactly.

The GitHub octocat mark is the one filled icon allowed — it's a recognizable brand mark.

### Logo
Two SVG paths, two linear gradients. The **sweep** path is the large arc; the **accent** path is the dot + ribbon.
- Sweep gradient: `#3B82F6 → #1E40AF`
- Accent gradient: `#22C55E → #15803D`

Canonical file at `assets/logo-current.svg`. Use the `--logo-sweep-start/end` and `--logo-accent-start/end` CSS variables rather than hard-coding the hex values, so the logo stays in sync with the palette if it ever moves.

### The wordmark
Currently displayed as **Tryggare** + `.app` (`.app` colored with `--brand-primary`). Because the `.app` domain is not owned, `.app` is **optional**. Treatments:

1. **`Tryggare`** alone — preferred for app shell, favicons, repo README, any case where the domain isn't guaranteed.
2. **`Tryggare.app`** — marketing site only, and only as long as we plan to acquire the domain.

When the domain decision is made, this section should be updated and one of these two treatments should be retired.

---

## Index

```
README.md                ← you are here
SKILL.md                 ← entry-point for Claude Code / Agent Skills
colors_and_type.css      ← all design tokens (brand + neutral + type + spacing)
assets/
  logo-current.svg       ← canonical 2-path logo (gradients as hex)
  logo.svg               ← copy of the original artist file
  checkin-screen.png     ← the phone screenshot used in the hero
preview/                 ← cards rendered in the Design System tab
ui_kits/
  landing/               ← React/JSX recreation of the landing page UI
    index.html
    *.jsx
```
