The Conference Child Management System has a product specification at `docs/specification.md` and an architecture/technical-design doc at `docs/architecture.md`.

`docs/roadmap/` contains lightweight stubs for low-priority future work. Each file is one topic; `docs/roadmap/README.md` is the index.

If you really have to write on-the-fly documentation or markdown summaries, store them under `docs/`.

Persistent dev helpers (anything reusable across sessions) go under `scripts/`. `agent-tools/` is a gitignored scratch directory: throw-away scripts you write during a session belong there and won't be committed.

## Deployment Environments

**Two deployment modes exist. Dev may not always be up — use `make status` to check.**

### Production Deployment (docker-compose.prod.yml)
- **Single container**: Django serves both API and built frontend static files
- **Access**: `http://localhost:8080` (both frontend and backend)
- **Database**: PostgreSQL on port 5433
- **Settings**: `config.settings.prod`
- **Auto-rebuild**: `make watch` (or `make watch-prod`) runs on the **host server** — not available to Claude Code (no podman access in the container). To trigger a rebuild, write to `restart.txt`.
- **Manual rebuild**: No podman access from Claude Code. The only way to trigger a rebuild is to write to `restart.txt`.
- **Testing**: `./verification.sh --test` (checks build logs, disk space, then runs tests)

### Development Environment (docker-compose.yml)
- **Separate containers**: Frontend (SvelteKit dev server) and Backend (Django)
- **Access**: Frontend `http://localhost:5173`, Backend `http://localhost:8000`
- **Database**: PostgreSQL on port 5432
- **Settings**: `config.settings.local`
- **Auto-rebuild**: `make watch` (or `make watch-dev`) runs on the **host server** — not available to Claude Code.
- **Restart**: Hot reloading should cover most code changes, but if you have to restart, trigger the auto-rebuild by writing to `checks-ins/restart.txt`.
- **Note**: `backend/config/settings/local.py` overrides `STATIC_URL = "/static/"` to avoid conflicts with `MEDIA_URL` in dev mode

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

