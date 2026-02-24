# Conference Child Management System

A check-in/check-out system for managing children at conference events. Staff can check children in and out across multiple stations, print name labels, and track attendance in real time.

## Stack

- **Backend:** Django 5.x + Django REST Framework + Django Channels (WebSockets)
- **Frontend:** SvelteKit (Svelte 5) + Tailwind CSS 3 + svelte-i18n
- **Database:** PostgreSQL 16
- **Message broker:** Valkey (Redis-compatible, for WebSocket broadcast)
- **Runtime:** Python via `uv`, Node via `pnpm`

## Environments

### Development (`docker-compose.yml`)

| Service | URL |
|---|---|
| Frontend (SvelteKit dev server) | http://localhost:5173 |
| Backend (Django/Daphne) | http://localhost:8000 |
| PostgreSQL | port 5432 |

Auto-rebuild on file change via hot reload. To force restart, write to `restart.txt`.

### Production (`docker-compose.prod.yml`)

| Service | URL |
|---|---|
| Django (serves API + built SPA) | http://localhost:8080 |
| PostgreSQL | port 5433 (internal) |

Auto-rebuild triggered by writing to `restart.txt`. Build log: `build.prod.log`.

## Quick Start (Dev)

```bash
# Start dev environment
podman compose up -d

# Run backend migrations
cd backend && uv run python manage.py migrate

# View logs
tail -f web.log          # Django backend
tail -f frontend.log     # SvelteKit frontend
tail -f build.dev.log    # Container build output
```

Login: `admin` / `admin123`

## Project Structure

```
backend/              Django project
  config/             Settings, ASGI/WSGI, URL routing
  accounts/           Admin user auth
  families/           Family, Parent, Child models + REST API
  checkins/           Check-in/out logic, WebSocket consumer
  events/             Events, Sessions, Tickets
  printing/           Label print queue
  tests/
    unit/             Django unit tests
    e2e/              Selenium browser tests

frontend/             SvelteKit project
  src/routes/         Pages: login, checkin, checkout, print-queue, qr/[id]
  src/lib/
    components/
      ui/             Generic components (Button, Card, Alert, etc.)
      checkin/        Check-in specific components
      checkout/       Check-out specific components
      domain/         Print queue table, family table
    api/              API client layer
    stores/           Svelte stores
    i18n/             Translation JSON (en, sv)

docs/                 Design documents, implementation notes
agent-tools/          Ad-hoc test/verification scripts
```

## Testing

```bash
make help              # All available commands

# From repo root
make test              # All tests (unit + E2E)
make test-e2e-dev      # E2E against dev (localhost:5173/8000)
make test-e2e-prod     # E2E against production (localhost:8080)

# From backend/
make test-auth         # Auth flow tests
make test-checkin      # Check-in flow tests
make test-checkout     # Check-out flow tests
make test-qr           # QR page tests
make test-print        # Print queue tests
make test-i18n         # i18n tests
make test-navigation   # Navigation tests
```

Baseline: ~20/23 E2E tests passing. 3 known gaps (WebSocket real-time, undo checkout, bulk check-in) - not regressions.

## Backend Model Changes

```bash
cd backend
uv run python manage.py makemigrations
uv run python manage.py migrate
make verify
```

## Key Design Decisions

- **One child = one session**: a child can only be checked in to one session at a time (enforced)
- **UUID QR tokens**: cryptographically secure, public read-only QR pages; actions require login
- **Real-time sync**: WebSocket via Django Channels broadcasts check-in/out events to all stations
- **i18n**: Swedish + English throughout (Django i18n backend + svelte-i18n frontend)
- **SPA in production**: SvelteKit builds to static files served by Django/WhiteNoise

## Documentation

- [Project Specification](./PROJECT_SPECIFICATION.md) - Requirements and data model
- [Technical Design](./TECHNICAL_DESIGN.md) - Architecture decisions
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Development roadmap and status
- [Current Tasks](./CURRENT_TASKS.md) - Active work
- [docs/](./docs/) - Design docs, API notes, deployment guides
