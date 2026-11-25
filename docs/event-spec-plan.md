# Event spec: an authoring format an LLM can read, validate, and apply

Implementation plan. Builds on `docs/form-spec-foundation-plan.md` (PR #30).
Branch: `feat/event-spec` (stacked on `feat/form-spec-foundation`).

## Goal

A structured way for an LLM (or a script) to learn what an event can contain, and tools to
export, validate, diff, and apply a full event spec. Validation is the core of it.

## Decisions (owner, 2026-11-19)

- **Full spec + diff.** Callers always submit a complete spec. No patch operations.
- **No human approval in the apply path.** It would break an agentic loop. Validation, staff
  permissions, and the empty-event rule are the guards; `apply` returns the diff as information.
- **Apply never opens registration.** A spec that would leave the registration window open at apply
  time is refused. A human opens registration in admin. This keeps the roadmap's "a human confirms
  before a form goes live" without gating config edits.
- **Apply targets** a new event, or an existing event that is empty (no registrations, issued
  tickets, or check-ins). Anything else is refused. No editing of events with registrations.
- **Interfaces:** staff REST API and `manage.py` commands. An MCP wrapper can come later.
- **No form-field config** in the spec yet; person fields stay code constants.
- **No pricing logic.** Prices are plain values; `registrations/pricing.py` stays the only pricing code.
- **pydantic v2** for the typed spec, parsing, path-addressed errors, and JSON Schema.
- **Row keys are derived from names** on export (slugified, unique per kind; promo codes use
  their code). No migration. A rename shows as remove + add in the diff.

## The spec (`event_spec_version: 1`)

Sections: `event`, `sessions`, `ticket_types`, `extras` (with `choices`), `promo_codes`.
Every row has a `key`; cross-references use keys, never UUIDs (e.g. `requires_ticket_type: "adult"`,
`sessions: ["sat-workshop"]`, promo `applies_to_ticket_types`/`unlocks_ticket_types`, extra `session`).
Field set = the model fields `copy_event` copies (see Step A in the foundation plan); derived
fields, counters, and timestamps are not in the spec.

## What the LLM gets (`GET /api/event-specs/schema/`)

- The JSON Schema, generated from the pydantic models, with a description on every field
  (units, currency, what min/max birthdate mean, which fields are optional, time zone).
- A capabilities list: what can be expressed, and named things that cannot (sibling discount,
  more than one promo code per registration, free-text extras, waitlists, family groups, line items),
  so the model can say "not supported" instead of inventing a field.
- A worked example: the "Test Conference 2027" brief from `docs/registration-setup-walkthrough.md`
  as a valid spec. The example is also a test fixture.

## Validation (errors block; warnings are returned)

Errors carry a JSON path (e.g. `ticket_types[2].min_birthdate`), a code, and a message, so an LLM
can fix and retry.

1. Shape: types, required fields, enums, unknown keys rejected (pydantic, `extra="forbid"`).
2. References: every key resolves, keys unique per kind, references point at the right kind.
3. Model rules: build unsaved model instances and run `full_clean()` on each, so existing rules
   (`TicketType._clean_age_window`, `Event.clean`, ...) are reused, not rewritten. Map their
   `ValidationError`s back to spec paths.
4. Going live: a registration window open at validation time is an error (see Decisions).
5. Setup checks (warnings; roadmap option C): age tier with no price, promo code whose ticket types
   are all inactive, hidden ticket type no active code unlocks, session bundle with no sessions,
   required extra with requires_choice but no active choices, etc.

## Services (`backend/events/event_spec/`)

- `export(event) -> spec`
- `validate(spec, event=None) -> (errors, warnings)`
- `diff(event, spec) -> list of changes` (added / changed field by field / removed, by kind and key)
- `apply(spec, event=None) -> (event, diff, warnings)`: one transaction; validate first; refuse
  non-empty events; update rows matched by key (ids stay stable), create new, delete removed.
- Round trip: for an event built by apply, `export` returns the same spec, and `apply(export(e))`
  onto an empty event yields equal config.

## Interfaces (staff only; same permission rule as the copy-event admin action)

- `GET  /api/event-specs/schema/` schema + capabilities + example
- `POST /api/event-specs/validate/` errors + warnings (optionally against an event id)
- `POST /api/event-specs/` apply as a new event
- `GET  /api/events/<id>/spec/` export
- `POST /api/events/<id>/spec/diff/` diff + warnings, no writes
- `PUT  /api/events/<id>/spec/` apply onto an empty event
- `manage.py event_spec export|validate|diff|apply` (apply takes `--event`, `--dry-run`)

## Steps

1. Spec models, JSON Schema, capabilities, example, `export`, `validate` (no writes).
2. `diff` and `apply`, empty-event guard, round-trip tests.
3. REST API and CLI.
4. Rebuild `copy_event` as export -> shift dates -> apply, so there is one copier. Its existing
   tests are the regression net.

Each step: implementation, review, fixes.

## Out of scope

Patch operations, editing events with registrations, versioning, form-field config, pricing in the
spec, MCP server, the assistant itself, opening registration via the spec.
