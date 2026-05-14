# Implementation Plan — Current State

> The original v1 plan (Next.js/T3 Stack) has been superseded. The system was implemented with Django + SvelteKit.

## Stack

- **Backend**: Django 5 + Django REST Framework, PostgreSQL, Django Channels (WebSocket)
- **Frontend**: SvelteKit + TypeScript + Tailwind CSS
- **Infrastructure**: Docker Compose (dev + prod), single-container production build

## Status: MVP Complete

All core features are implemented and in production:

- Check-in and check-out flows (search by name or QR/ticket code)
- Session management (one child = one active session enforced)
- QR code system (short alphanumeric pool, allocated per check-in)
- Ticket system (EventTicket and SessionTicket, polymorphic)
- Label printing (WebSocket-based print queue, printer client integration)
- Data import: FestivalPro (multi-step wizard, field mapping, idempotent re-import)
- Data import: Planning Center (household/member sync)
- i18n: Swedish and English
- Audit logging
- Admin user management

## Where to find current work

- **In-progress tasks**: `CURRENT_TASKS.md`
- **Future ideas / deferred work**: `DEFERRED_TASKS/` (see `DEFERRED_TASKS/README.md` for index)
- **Architecture details**: `TECHNICAL_DESIGN.md`
- **Project specification**: `PROJECT_SPECIFICATION.md`
