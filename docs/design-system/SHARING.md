# Sharing styles & components with the marketing site

The app (SvelteKit, `main`) and the marketing landing page (`gh-pages` branch, a single
static `index.html`) currently re-declare the same brand values by hand, which drifts. This
documents how to share — honestly, what *can* and *can't* be shared given the two stacks.

> Status: the **app side is done** (token layer below). The **marketing side is a plan** — the
> landing page has a pending update, so no `gh-pages` change has been made yet. Apply the
> marketing steps when that update lands.

## Tokens — genuinely shareable (do this)

The token layer (colors, type, radii, shadows) is plain CSS custom properties and is identical
for both surfaces. Make it one file that both consume:

1. **Canonical file:** `frontend/src/lib/styles/tokens.css` is the single source of truth. The
   app imports it globally and mirrors the values into `tailwind.config.cjs` (guarded by
   `npm run check:tokens`).
2. **Marketing consumes the same file.** When the pending marketing update lands, replace the
   inline `:root { … }` block in `gh-pages/index.html` with a link to a committed copy of the
   canonical tokens:
   ```html
   <link rel="stylesheet" href="tokens.css" />
   ```
   Commit a copy of `tokens.css` onto `gh-pages` next to `index.html` (GitHub Pages serves the
   branch as-is, so the file just needs to be present).
3. **CI guard against drift.** Add a job (on `main`) that fetches the `gh-pages` copy of
   `tokens.css` and diffs it against the canonical one — fail on mismatch (checksum compare).
   This is the same "copy + CI guard" pattern the in-app guard uses, extended across branches.
   Near-zero infrastructure, no publishing step.

   *Graduation path (optional, later):* publish the tokens as an npm package
   (`@tryggare/tokens`) and have both surfaces depend on it. More setup; only worth it if a
   third surface appears.

## Components — not shareable as code (today)

Component **code** can't cross the SvelteKit ↔ static-HTML boundary without giving the
marketing site a build step:

- The app's primitives are Svelte components (`Logo.svelte`, `Button.svelte`, …).
- The marketing site is hand-written HTML using plain CSS classes (`.btn`, `.feature-card`,
  `.lang-toggle`) plus an inline `T = { en, sv }` i18n block.
- The `ui-kit-reference/*.jsx` files are **neither** — they're a written spec.

Two honest paths:

- **Cheap (recommended for now):** keep the marketing site's plain CSS classes, but have them
  consume the shared `tokens.css` (they already use `var(--…)`). Treat the JSX/Svelte
  primitives as a **shared written spec** (`ui-kit-reference/` + `DESIGN_SYSTEM.md`),
  implemented once per framework. Tokens stay in lockstep; component *shapes* stay consistent
  by spec, not by shared code.
- **Real component sharing (bigger, future):** migrate the landing page into this SvelteKit
  app as a statically-built marketing route and publish that build to `gh-pages`. Then
  `Logo` / `Button` / `Pill` are literally the same Svelte components on both surfaces. Out of
  scope now; revisit only if the marketing site gains a build pipeline.

## Net recommendation

Share the **token layer now** (mechanically, with a CI guard); share **component specs, not
code**; revisit full component sharing only if/when the marketing site gets a build step.
