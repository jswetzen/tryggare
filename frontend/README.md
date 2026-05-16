# Check-ins Frontend

SvelteKit (Svelte 5 runes) + Tailwind CSS + svelte-i18n. Builds to a static SPA served by Django in production; runs as a hot-reloading dev server in development.

See the [top-level README](../README.md) for project overview and how to run the full stack.

## Commands

```bash
# Install dependencies
pnpm install

# Dev server (usually started via docker compose at repo root; runs at http://localhost:5173)
pnpm dev

# Type-check
pnpm check

# Production build
pnpm build

# Unit tests (Vitest)
pnpm test
```

## Layout

```
src/
  routes/          Pages: login, checkin, checkout, print-queue, qr/[id]
  lib/
    components/
      ui/          Generic components (Button, Card, Alert, …)
      checkin/     Check-in specific
      checkout/    Check-out specific
      domain/      Print queue and family tables
    api/           API client
    stores/        Svelte stores
    i18n/          Translations (en, sv, nb)
```

New user-facing strings must have entries in `src/lib/i18n/{en,sv}.json` (see CONTRIBUTING.md for details).
