# Check-ins Backend

Django 5 + Django REST Framework + Django Channels. Serves the API, runs the print queue, and broadcasts WebSocket events to connected stations.

See the [top-level README](../README.md) for project overview and the [architecture doc](../docs/architecture.md) for design details.

## Commands

```bash
# Install dependencies
uv sync

# Database
uv run python manage.py migrate
uv run python manage.py createsuperuser

# Dev server (usually started via docker compose at repo root)
uv run python manage.py runserver

# Tests
make help            # All test targets
make test-unit       # Unit tests
make test-e2e-dev    # E2E (requires running dev env)

# Lint / format (CI enforces these)
uv run ruff check .
uv run ruff format .
```

See [`TESTING_QUICKSTART.md`](TESTING_QUICKSTART.md) for a deeper test walkthrough.

## Layout

```
accounts/    Admin user model and auth
families/    Family, Parent, Child models + REST API
events/      Event, Session, Ticket models
checkins/    Check-in/out logic, WebSocket consumer, audit log
printing/    Printer + PrintJob models, label queue
imports/     FestivalPro and Planning Center importers
config/      Settings (base/dev/local/prod/test), URL routing, ASGI/WSGI
tests/
  unit/      Pure-Django unit tests (run in CI)
  e2e/      Selenium browser tests (run against live dev env)
scripts/     Helper scripts (seed data, demo)
```
