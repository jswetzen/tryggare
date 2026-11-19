# Form builder foundation: spec, event copy, spec-driven renderer

Implementation plan for the first building blocks of `docs/roadmap/registration_form_builder.md`.
Branch: `feat/form-spec-foundation` (off `main`).

## Decisions (owner, 2026-11-19)

- The spec is a **read-only projection of the existing models**. Models stay the source of truth.
  No stored spec, no draft/publish, no editor, no assistant.
- The spec carries **no pricing logic**. `registrations/pricing.py` stays the only pricing code.
- **One renderer.** `frontend/src/routes/register/[eventId]/+page.svelte` is changed to read the
  spec; no parallel renderer.
- "Hot reload" at this stage = the preview page can **reload the form from the model** on demand.
  No WebSocket/live push until the spec is done.
- Event copy = **whole event, dates shifted**, with an `Event.cloned_from` FK for provenance.

## Step A: event copy (`backend/events/`)

- `copy_event(source, *, name, start_date) -> Event` in `events/services.py`, one transaction.
- Copies: event settings, sessions, ticket types, extras + choices, promo codes. Preserves `is_active` on ticket types, extras, choices and promo codes; copied sessions start inactive (live check-in state).
- Remaps internal references to the new rows: `TicketType.sessions`, `TicketType.requires_ticket_type`,
  `Extra.session`, `PromoCode.applies_to_ticket_types`, `PromoCode.unlocks_ticket_types`.
- Shifts every date by `new start_date - source.start_date`: event end_date, registration window,
  session start/end, `TicketType.available_from/until`, `TicketType.min/max_birthdate` (age tiers, rebuilt from the new start date so they stay on the anniversary `_clean_age_window` requires),
  `PromoCode.valid_from/until`. Datetimes shift in Europe/Stockholm wall-clock time (DST-safe).
- Resets `PromoCode.uses_count`. Never copies registrations, attendees, tickets
  (`Ticket`, `EventTicket`, `SessionTicket`), or check-in data.
- New nullable `Event.cloned_from` FK (`SET_NULL`) + migration; shown read-only in admin.
- Django admin action "Copy event" with an intermediate form (new name, new start date), redirecting
  to the new event's change page. One source event per action.

## Step B: form spec (`backend/registrations/`)

- `registrations/form_spec.py`: `build_form_spec(event) -> dict`. The body of
  `registration_event_info` moves here; the view becomes a thin wrapper on the same URL
  (`/registrations/events/<id>/`). That URL's only consumer is `registrationApi.getEvent`.
- Keeps every current key. Adds:
  - `spec_version: 1`
  - `sessions`: id, name, start/end for sessions referenced by the form (extras' `session_id`, ticket types).
  - `fields`: the person/registration fields that are hardcoded today (parent: first/last name, phone,
    email, relationship, allergies, notes, health consent; child: first/last name, birthdate,
    allergies, notes, health consent), each `{key, visible, required}`. From code constants for now.
  - `required` means "the form requires it" (today's page behaviour), not "the server requires it". Fields the page requires but the server accepts blank are listed in `FORM_ONLY_REQUIRED` (child last name, birthdate) and Step C must not loosen them. `contact_email` is registration-level and not in the spec yet.
- Response header `Cache-Control: no-store`.
- Tests: the spec's `required` flags agree with what submit actually enforces; a JSON fixture
  generated from a fixture event is written to `frontend/src/lib/registration/__fixtures__/form-spec.v1.json`
  and a test fails if it is stale (regenerate with an env flag).

## Step C: renderer reads the spec (`frontend/`)

- `RegistrationFormSpec` type (replaces/extends `RegistrationEventInfo`), checked against the fixture.
- `$lib/registration/formSpec.ts`: the page's pure selection helpers move here with unit tests
  (`applicableTicketTypes`, `applicablePersonExtras`, `registrationExtras`, field lookups).
- `PersonFields.svelte` renders person fields from `spec.fields`. The rest of the page stays where it is.
- In `?preview=1`: a "Reload form config" button re-fetches the spec and re-renders, keeping entered
  data. Selections pointing at ticket types/extras/choices that no longer exist are cleared, with a notice.
- Existing `page.test.ts` stays green; i18n strings in both locales.

## Verification

- Backend: `manage.py test` and `uv run pytest tests/unit/` (see CLAUDE.md, both are needed).
- Frontend: `npm run check`, vitest.
- Dev stack: edit a ticket price in admin, press Reload in preview, the new price shows.

## Out of scope

Pricing in the spec, shared basket function (roadmap step 6), draft/publish (step 7), editor,
configurable fields storage, WebSocket live updates, assistant, setup checker.
