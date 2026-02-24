# Django + SvelteKit Migration Plan

This plan describes how to transition the existing Next.js/tRPC application to the Django + SvelteKit architecture defined in `TECHNICAL_DESIGN.md`. It preserves the current relational data model (families, parents, children, events, sessions, tickets/passes, check-in/out records, audit logs, admin users) while replacing the runtime stack.

## Phase 1: Repository Reboot and Environments
- **Backend project bootstrapping**
  - Create a new Django 5 project (e.g., `backend/`) with apps for `accounts`, `families`, `events`, `checkins`, and `printing`.
  - Add Django REST Framework, Django Channels, django-cors-headers, and Valkey/Redis channel layer configuration.
  - Configure settings modules for `local`, `dev`, and `prod` with environment-variable driven secrets and database URLs.
- **Frontend project bootstrapping**
  - Initialize a SvelteKit SPA (TypeScript + Tailwind) under `frontend/` with pnpm.
  - Add svelte-i18n, shadcn-svelte (optional), and shared UI/layout primitives.
- **Docker and compose refresh**
  - Replace the current Node-only compose files with multi-service definitions: `web` (Django/Daphne), `frontend` (static build or dev server), `db` (PostgreSQL 16), and `valkey` for Channels.
  - Provide `.env.example` files for both Django and SvelteKit and align health checks with Daphne and Postgres.

## Phase 2: Data Model Migration
- **Schema translation**
  - Translate the Prisma models into Django models within the relevant apps (e.g., `families.models.Family`, `children.models.Child`, `events.models.Event/Session`, `checkins.models.CheckInRecord`, `tickets.models.Ticket`/`Pass`).
  - Preserve constraints: unique QR token per child, one active session per child, admin user attribution on check-in/out, and audit trails.
- **Migrations and seeds**
  - Generate initial Django migrations and write fixtures/management commands to seed the database with existing sample data.
  - Plan a one-time data import script that reads the current Postgres schema (via Prisma tables) and migrates rows into the Django schema if continuity is required.

## Phase 3: Authentication and Authorization
- **Admin users**
  - Use Django’s auth system with a custom user model (username, password hash, name, last login, active flag).
  - Configure the Django admin for CRUD on all entities with appropriate list filters and search fields.
- **Session and CSRF**
  - Enable session-based auth for REST and Channels; include CSRF middleware and CORS settings for the SvelteKit origin.
  - Add permission classes in DRF to guard admin-only APIs and expose select read-only endpoints (e.g., QR public info).

## Phase 4: API + Realtime Layer
- **REST endpoints (DRF)**
  - Implement viewsets/routers for families, children, events/sessions, tickets/passes, and check-in/out actions.
  - Validate the “one child in one session” rule at the serializer or service layer; return actionable errors for conflicts.
- **WebSockets (Channels)**
  - Create consumer(s) for real-time updates (check-in/out broadcasts, session status) using Valkey as the channel layer.
  - Ensure permission checks and group-based broadcasting so check-in stations receive live updates.

## Phase 5: Printing and QR Codes
- **Server-side printing pipeline**
  - Add a printing service module that renders labels (Python qrcode + Pillow/templating) and sends raw jobs to configured printers (CUPS/TCP). Configure via environment variables.
  - Provide DRF endpoints for initiating prints and reprints; log results for troubleshooting.
- **QR token handling**
  - Generate UUID QR tokens on first check-in; expose a public read-only endpoint for `/qr/<token>` with child info and current status.

## Phase 6: Frontend Feature Parity in SvelteKit
- **Routing and data layer**
  - Build SvelteKit routes for check-in, check-out, QR info, admin-lite views, and printing flows. Use Fetch/REST clients for CRUD and WebSocket connections for live updates.
  - Implement shared stores/helpers for session selection, family search, and error handling that mirror existing UX.
- **UI and i18n**
  - Port Tailwind styles and shadcn components where applicable; ensure mobile-friendly layouts for kiosk usage.
  - Reuse translation content via svelte-i18n, importing existing locale strings where possible.

## Phase 7: Testing and Observability
- **Backend testing**
  - Add Django TestCase suites for model rules (single active session), serializers, API endpoints, and Channels consumers.
  - Include printing service unit tests with a stub driver.
- **Frontend testing**
  - Use Playwright or Vitest for key Svelte flows (check-in, check-out, QR page) and contract tests against the REST API.
- **Monitoring and logging**
  - Configure Django logging with structured output, health endpoints, and basic metrics. Set up frontend error reporting hooks.

## Phase 8: Cutover Strategy
- Stand up the Django + SvelteKit stack in parallel with the existing app using a fresh database.
- Import or reseed data, validate parity of core flows, and run smoke tests.
- Switch traffic to the new stack once check-in/out, QR pages, and admin CRUD are verified, keeping rollback plan (restore previous Docker compose) available.
