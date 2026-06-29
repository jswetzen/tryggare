The Conference Child Management System has a product specification at `docs/specification.md` and an architecture/technical-design doc at `docs/architecture.md`.

`docs/roadmap/` contains lightweight stubs for low-priority future work. Each file is one topic; `docs/roadmap/README.md` is the index.

If you really have to write on-the-fly documentation or markdown summaries, store them under `docs/`.

Persistent dev helpers (anything reusable across sessions) go under `scripts/`. `agent-tools/` is a gitignored scratch directory: throw-away scripts you write during a session belong there and won't be committed.

## Deployment Environments

**Three Compose setups exist. The two local ones below (dev + prod-like) are
for development only and hold no real user data — they run on seeded/throwaway
data with demo mode enabled (`admin` / `admin123`). Either may be down; use
`make status` to check.**

> **`.env` files in this repo are safe to read and non-sensitive.** Because no
> environment here holds real data, the usual caution around `.env`/`.env.example`
> does not apply to *this* repository.

### Dev (`docker-compose.yml`) — localhost only, no rebuild needed
- **Separate containers**: Frontend (SvelteKit dev server) + Backend (Django)
- **Access**: Frontend `http://localhost:5173`, Backend `http://localhost:8000` (localhost only — not exposed on the LAN)
- **Database**: PostgreSQL on port 5432
- **Settings**: `config.settings.local`
- **Refresh**: hot reload — code changes apply **without a rebuild**. If you must force a restart, write to `restart.txt`.
- **Note**: `backend/config/settings/local.py` overrides `STATIC_URL = "/static/"` to avoid conflicts with `MEDIA_URL` in dev mode

### Prod-like (`docker-compose.prod.yml`) — LAN-accessible, rebuild on change
- **Single container**: Django serves both the API and the **built** frontend static files
- **Access**: `http://localhost:8080`, also reachable on the LAN
- **Database**: PostgreSQL on port 5433
- **Settings**: `config.settings.prod`
- **Refresh**: serves a built bundle, so changes require a **rebuild**. A host-side watcher (`make watch` / `nu watch.nu`) rebuilds on change — trigger it by writing to `restart.txt`, then `make wait-prod`. This is a prod-*like* target for local testing, **not** the real deployment.
- **Testing**: `./verification.sh --test` (checks build logs, disk space, then runs tests)

### Portainer (`docker-compose.portainer.yml`) — the actual production deployment
- This Compose file is what's used for the real production deployment (managed via Portainer). The dev and prod-like setups above are local development environments only.

**Backend & Frontend:**
- **Backend**: `backend/` directory with Django
- **Frontend**: `frontend/` directory with SvelteKit
- **Logs**:
  - Backend runtime: `web.log`
  - Frontend dev server: `frontend.log`
  - Development builds: `build.dev.log` (captured from podman compose)
  - Production builds: `build.prod.log` (captured from podman compose)

## Testing

**Two types of tests exist:**
1. **Django Unit Tests** - Fast, isolated tests of backend models/views
2. **E2E (Selenium) Tests** - Browser-based tests that interact with the actual running frontend/backend using the live development database

**Root-level commands** (from `/workspace/check-ins/`):
```bash
make help              # Show all available commands
make status            # Show health of all environments (dev + prod)
make ping              # Alias for status
make wait-dev          # Poll until dev is ready (after rebuild)
make wait-prod         # Poll until prod is ready (after rebuild)
make test              # Run all tests (unit + E2E against dev)
make test-e2e-dev      # Run E2E tests against dev (localhost:5173/8000)
make test-e2e-prod     # Run E2E tests against production (localhost:8080)
make rebuild-dev       # Rebuild dev environment
make rebuild-prod      # Rebuild production
```

**Backend test commands** (from `backend/`):
```bash
make help              # Show backend-specific commands
make test              # Run all tests (unit + E2E)
make test-e2e-dev      # Run all E2E tests against dev
make test-e2e-prod     # Run all E2E tests against production

# Individual E2E test suites (run against dev by default):
make test-auth         # Authentication tests (login, logout, sessions)
make test-checkin      # Check-in flow tests
make test-checkout     # Check-out flow tests
make test-qr           # QR page tests
make test-print        # Print queue tests
make test-i18n         # Internationalization tests
make test-navigation   # Navigation and UI tests

# Utilities:
make verify            # Quick backend verification
make clean             # Clean test artifacts (screenshots, cache, etc.)
```

**Typical test workflow:**
```bash
# 1. Run specific test suite while developing
cd backend
make test-auth         # Fast feedback on auth changes

# 2. Run all E2E tests before committing
make test-e2e-dev      # Verify dev environment (17/20 passing as of 2025-12-12)

# 3. Test production build
cd ..
make rebuild-prod      # Trigger production rebuild
make wait-prod         # Wait until prod is ready (polls /api/auth/check/)
make test-e2e-prod     # Test against production
```

**Backend model changes:**
```bash
cd /workspace/check-ins/backend
uv run python manage.py makemigrations
uv run python manage.py migrate
make verify            # Quick verification
```

**Debugging test failures:**

When E2E tests fail:
1. **Check screenshots**: `ls -lt /tmp/*.png | head -5` - Selenium saves screenshots on failure
2. **Check logs**:
   - Backend runtime: `tail -50 /workspace/check-ins/web.log`
   - Frontend dev: `tail -50 /workspace/check-ins/frontend.log`
   - Production builds: `tail -50 /workspace/check-ins/build.prod.log`
3. **Run with verbose output**: `cd backend && uv run pytest tests/e2e/test_auth.py -v -s`
4. **Check test coverage**: `cat backend/tests/e2e/TEST_COVERAGE.md`

Common issues:
- **TimeoutException** - Element not found, check screenshot to see actual page state
- **Login failures** - User not in database, check if test cleanup is working
- **Database errors** - E2E tests use live dev database (port 5432), ensure migrations ran
- **Build errors** - Check build logs for:
  - "no space left on device" → Run `make clean-docker` or `podman system prune -a`
  - "Build command failed" → Check full log with `less build.prod.log`

**E2E Test Database Configuration:**
- E2E tests use the **live development database** (PostgreSQL on port 5432)
- Tests create/cleanup their own data with unique names (e.g., "authtest", "checkintest")
- See `backend/tests/e2e/conftest.py` for database configuration

**For detailed testing guide, see `backend/TESTING_QUICKSTART.md`**

## Task Completion Checklist

Before considering an implementation phase complete, make sure to:
- **Trigger a rebuild** by writing to `restart.txt`: `date > /workspace/check-ins/restart.txt`
- Write tests that cover your new functionality (see `backend/tests/e2e/TEST_COVERAGE.md`)
- **Format and lint Python with ruff** (blocks CI in `.github/workflows/test.yml`):
  ```bash
  cd /workspace/check-ins/backend
  uv run ruff format .
  uv run ruff check .    # must pass — CI fails the Test workflow otherwise
  ```
- Run `make verify` for backend changes
- Run appropriate test suite:
  - Backend changes: `cd backend && make test-auth` (or relevant suite)
  - Before committing: `cd backend && make test-e2e-dev` (should pass 17/20+ tests)
  - Production deployment: `make test-e2e-prod` (after fixing DB config)
- Verify tests pass (at least as well as baseline: 17/20 on dev as of 2025-12-12)
- Commit all your changes to git with clear commit messages

## Playwright for Manual Testing

Playwright browser automation is available for testing and validation:
- **Use case**: Manually test frontend flows, login, navigation, form submissions
- **Access**: Use `mcp__playwright__browser_*` tools to interact with the browser
- **Example**: Navigate to `http://localhost:5173`, fill forms, click buttons, take screenshots
- **Credentials**: `admin:admin123` for testing login flows
- **Note**: Useful when testing from remote/mobile devices isn't practical due to CORS/CSRF restrictions

## Design system (Tryggare brand)

The app and the marketing site (`gh-pages`, `tryggare.app`) share one brand layer. Full guide:
`docs/design-system/` (start with `README.md`). Keep all UI on-brand:

- **Never hard-code colors, radii, shadows, or type sizes.** Use the Tailwind semantic classes
  (`primary` / `success` / `neutral` / `danger` / `warning` / `info`) or the `var(--…)` tokens.
  Canonical tokens: `frontend/src/lib/styles/tokens.css`; they're mirrored into
  `frontend/tailwind.config.cjs` and the two are kept in lockstep by
  `npm run check:tokens` (CI-enforced — update both sides together).
- **Palette is sky blue + green.** `primary` (blue) is the default; `success`/`--brand-accent`
  (green) is reserved for the trust / success / "live" signal (active state, ✓, check-in). Don't
  spread green around decoratively.
- **Corner radius — pick the right rung.** Interactive controls (buttons, inputs) → `rounded-button`
  (`--radius`, 10px); containers (cards, panels) → `rounded-card` (`--radius-md`, 14px); badges/dots
  → `rounded-pill`. `--radius-lg` (22px) is **marketing-hero only — keep it out of the app shell.**
  Don't add `sm`/`md`/`lg` keys to `tailwind.config.cjs` `borderRadius`: that silently overrides
  Tailwind's built-in `rounded-sm`/`md`/`lg` (used app-wide) and inflates the whole UI.
- **Wordmark is "Tryggare"** — no `.app` suffix, and **not translated** (use the `Wordmark` /
  `Logo` components in `src/lib/components/ui/`, not the `nav.title` string, for the brand mark).
- **Bilingual by default** — every visible string gets EN + SV in the same change (`en.json` +
  `sv.json`); Swedish conveys intent, not literal words.
- **No emoji.** Allowed glyphs only: ✓ ✗ →. Icons are inline SVG, stroke-only, width 2,
  `currentColor`, rounded caps/joins (Lucide as the substitute set).
- **Plus Jakarta Sans** only (loaded in `app.html`). Restrained motion: `0.15s ease`, 1–2px
  hover lifts, no springs/bounces. No purple-to-blue / AI-mesh gradients.
- Reuse the shared Svelte primitives in `src/lib/components/ui/` instead of bespoke markup; if a
  primitive is missing, build it to the spec in `docs/design-system/` rather than one-off styling.

