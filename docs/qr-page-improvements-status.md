# QR-scan landing page — improvements (shipped)

**Page:** `frontend/src/routes/qr/[token]/+page.svelte` — the page staff land on when
they **scan the QR code on a printed child label** (post-scan info/action page, not a
"show a QR code" page).

## What changed

### 1. i18n — removed hardcoded strings
The `"Supervised"` badge and the old fake-QR modal strings now use `$t(...)`. Added keys
to both `en.json` and `sv.json` under `qr`: `supervised`, `age`, `ageYears` (interpolated
`{years}`), `allergyAlert`, `reprintSending`, `reprintSuccess`, `reprintError`,
`reprintOpeningPage`, `choosePrinter`, `choosePrinterHelp`.

### 2. Reprint label → real print flow
The old "Reprint Label" button opened a modal that only displayed the QR URL as text. It
now mirrors `print-queue/+page.svelte`:
- **Logged-in staff + exactly one online printer** → `printingApi.createJob({ checkin_id, printer_id })` (auto-print over WebSocket).
- **Logged-in staff + multiple online printers** → printer-picker modal (chosen over auto-picking the first).
- **Not logged in / no online printer** → opens `printQueueApi.getPrintPageUrl(...)` in a new tab (bounces to login if needed).

Printers load via `printingApi.getPrinters()` in an `$effect` gated on `$authStore.user`
(the QR endpoint is `AllowAny`, but print endpoints require auth). The fake QR-display
modal was deleted.

### 3. Visual polish
- **Allergy alert banner**: when `child.allergies` is set, a red-bordered `role="alert"`
  ⚠️ box renders at the very top, above the info card (safety info above the fold).
- **Age**: computed from `birthdate` (whole years, `$derived.by`) shown beside the name.
- Child name promoted to the card `<h1>`.

## Build / deploy fixes made to ship this
- **`frontend/package.json`**: pinned `"packageManager": "pnpm@9.15.9"`. The dev frontend
  Dockerfile had no pin, so corepack pulled pnpm 11, which turns ignored build scripts into
  a *fatal* error and broke the dev container build. (`backend/Dockerfile.prod` already
  pinned pnpm 9, so prod was unaffected.)
- **`.dockerignore`**: bare patterns (`node_modules`, `.pnpm-store`) only match the
  context root. The prod build uses the repo root as context (`COPY frontend ./`), so
  `frontend/node_modules` + `frontend/.pnpm-store` (~0.5 GB) were being copied into the
  image — that filled the disk and aborted the prod build. Added `**/` globs.
- **`scripts/ensure-prod-network.sh`** + **`watch.nu`**: `docker-compose.prod.yml` declares
  the `traefik` network as `external: true`. On hosts without a traefik deployment, `up`
  aborts with "External network [traefik] does not exists" before building. The script
  creates it idempotently and `watch.nu` runs it before every prod rebuild.

## Verification
- `svelte-check`: 31 errors / 56 warnings, baseline-identical, **0 in the QR page**.
- **8/8 QR E2E tests pass** (`backend/tests/e2e/test_qr_page.py`) against dev — including 4
  new tests: allergy banner (role=alert, above the card), age display, no-banner case, and
  reprint logged-out fallback. Tests are language-agnostic (app defaults to Swedish).
- Verified live on **dev** (`:5173`) and the **prod** build (`:8080`).

## Open follow-ups (not done)
- The locale files still carry orphaned "undo checkout" strings (`undoCheckOut`,
  `undoSuccess`, `canUndo`, `checkedOutAt`, `undoTooLate`) for an unimplemented feature
  (spec `docs/specification.md:155`). Either implement undo-checkout or remove the strings.
