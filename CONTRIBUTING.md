# Contributing to Tryggare

Thanks for your interest in Tryggare! Contributions of all kinds are welcome — whether you are a church volunteer with a bug report or a developer sending a pull request.

---

## Track A — Church and organization users

You do not need to write code to contribute. The most useful things you can do:

### Report a bug

1. Open an issue on GitHub.
2. Describe what you expected to happen and what actually happened.
3. Include your browser (if it is a frontend issue) and roughly how many families / children you are managing.
4. A screenshot is often worth a thousand words.

### Request a feature

Open an issue and describe the workflow you need. Real-world use cases ("at our conference we need X because Y") are far more useful than abstract feature descriptions.

### Share a configuration tip

If you got printer integration working, figured out a tricky Docker networking setup, or found a good way to import data — please share it. Open an issue or start a discussion so it can find its way into the docs.

---

## Track B — Developers

### Getting started

1. Fork the repository on GitHub.
2. Clone your fork and create a feature branch:
   ```bash
   git checkout -b my-feature
   ```
3. Start the dev environment:
   ```bash
   podman compose up -d
   cd backend && uv run python manage.py migrate
   ```
4. The frontend hot-reloads at `http://localhost:5173`. The backend runs at `http://localhost:8000`.
5. Run `make help` from the repo root to see all available commands.

### Code style

**Backend (Django / Python)**
- Follow PEP 8. The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.
- Run `ruff check .` and `ruff format .` before committing.
- Keep Django views thin; put business logic in model methods or service functions.

**Frontend (SvelteKit / Svelte 5)**
- Follow the Svelte 5 runes API (`$state`, `$derived`, `$effect`) — avoid the legacy Options API.
- Use Tailwind utility classes; avoid inline `style` attributes.
- New user-facing strings must have translations in both `en.json` and `sv.json` under `frontend/src/lib/i18n/`.

### Tests

Before opening a pull request, make sure the E2E suite still passes:

```bash
# From the repo root
make test-e2e-dev
```

The baseline is roughly 20/23 tests passing. Do not regress below that. If you are adding a new feature, add a test for it in `backend/tests/e2e/`.

For faster iteration while developing:

```bash
cd backend
make test-auth      # or test-checkin, test-checkout, test-print, etc.
```

### Submitting a pull request

- Keep PRs focused. One feature or fix per PR.
- Write a clear description of what changed and why.
- Reference any related issues with `Closes #123`.
- Migrations must be included if you changed a model.
- Run `make verify` from `backend/` to do a quick sanity check before pushing.

### Project layout

```
backend/    Django 5 — models, REST API, WebSocket consumers, print queue
frontend/   SvelteKit — check-in UI, QR pages, print queue view
docs/       Design docs and deployment notes
```

`make help` (from the repo root) shows every available command.

---

Questions? Open an issue or start a GitHub Discussion. We are happy to help.
