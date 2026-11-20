# Setup checker and extra gating: handover

Handover for a fresh session. Branch `feat/setup-checker` is local, stacked on `feat/event-spec`
(PR #31), which is stacked on `feat/form-spec-foundation` (PR #30). Neither PR is merged yet.
Don't push or open a PR unless the owner asks.

## Read first

1. `CLAUDE.md`.
2. `docs/event-spec-plan.md`: the spec, validation layers and guards this builds on.
3. `docs/trials/2026-11-19-agent-ui-trial.md` and `docs/trials/2026-11-19-feature-requests.md`:
   the evidence. The FR numbers below refer to that file.
4. `docs/roadmap/feature_requests.md`: this work is its phases 1 and 2.
5. `backend/events/event_spec/`: `_validate.py` (warnings are split per kind, messages live in one
   `MESSAGES` table) and `_kinds.py` (one table drives export, diff, validate, apply, copy shift;
   its docstring says what a new field or reference touches).

## Part A: setup checker in admin (FR-5, plus new warnings)

The checker is `validate(export(event), event)` on a live event. Its warnings exist; staff can't
see them without the CLI. Today they show only after an admin copy.

1. **`manage.py event_spec check --event ID`**: export, validate, print errors and warnings. It is
   a convenience over `export | validate`. Exit 1 on errors, as `validate` does.
2. **Admin "Check setup"** on the Event change list (action) and change page (button or panel).
   Show errors and warnings with human row names, not just spec paths: `ticket_types[3]` should
   read as "Ticket type 'Child pass 13-17'". `registration_open_on_target` and `event_not_empty`
   are apply guards, not setup problems; leave them out of this view.
3. **New warnings** (FR codes; the codes are the trial file's proposals, rename if needed):
   - `bundle_replaces_pass` (FR-1, FR-2): a `session_bundle` whose age window and `applies_to`
     overlap an active event ticket, or that requires one, can never be bought alongside it.
     This fires on today's `example.json`; fixing the example is Part B.
   - `ticket_rule_open_with_tickets` (FR-3): event default ticket rule is open while it has
     active ticket types, so anyone checks in at the door without a pass.
   - `event_price_ignored` (FR-3): `Event.price` is set while ticket types exist. It is ignored
     until every ticket type is inactive, then silently comes back (`pricing.calculate_total`).
   - `age_band_gap`, `age_band_overlap` (FR-10): ages with no active ticket of a kind and
     audience, or two active tiers covering the same age.
   - `inactive_unreferenced` (FR-11): an inactive row that nothing refers to; it gets copied.
4. Each warning gets a code in `MESSAGES` (sv + en), one line in its per-kind function, and a
   test. Add the new codes to the capabilities notes if the schema response lists them.
5. **Feature-request link (design phase 2), only if cheap:** a per-warning "intended: the product
   can't do this" link that opens a prefilled request. A prefilled GitHub `issues/new` URL is
   enough; no model yet (phase 3). Skip it if it grows; say so in the report.

## Part B: extras gated by ticket type (FR-1, decided)

**Owner decision (2026-11-19):** an extra can require one or more ticket types. This is the
`Extra.ticket_types` M2M that the case catalog deferred in §3.4 until a real case appeared; the
trial is that case. Not an age window on Extra, and not "pass plus bundle" on the public form.

- **Semantics (proposed; confirm with the owner if the code argues otherwise):** empty means no
  gate, as today. Non-empty, per-attendee extra: offered to an attendee holding *any* of the
  listed types. Registration-level extra: offered when any attendee in the registration holds one.
- **Where it lands:** model + migration (additive), admin (filter the picker to the extra's event:
  FR-6 is the same bug for sessions and "bought together with"), the server-side selection check
  in `registrations/`, the form spec (`registrations/form_spec.py`) so the public form hides or
  disables the extra with a reason, pricing untouched (`pricing.py` only prices what was
  selected), and the event spec: a `ticket_types: list[Key]` on `ExtraSpec` plus one `refs` entry
  in `_kinds.py` and its line in `_apply._write`.
- **Then fix the example:** `example.json` models the 13-17 workshop as a `session_bundle`. Make
  it a session-scoped extra gated on the 13-17 pass, and give the event a ticketed door rule
  (it is `"open"`, FR-3). The test that the example validates with no warnings keeps it honest.
- **Capabilities:** add "an add-on limited to holders of given ticket types" to supported.
- Update FR-1 and FR-2 in the trial file to `status: accepted`, pointing at the commit.

## Decisions (2026-11-20)

- **Door rule in the example:** event default `all`, the workshop session `children`. Guardians who
  only drop off children never need a ticket under any rule, so `all` does not block them. `children`
  at event level would leave the adult pass unenforced at the door.
- **Bundle holders:** an attendee holding a session-bundle ticket type counts as holding that type
  for an extra's gate. The alternative makes a bundle ungateable and has no case in its favour.
- **Known limit:** the door checks tickets, not extras. Admission to a session with an add-on extra
  is not checked against the extra: see FR-17 in `docs/trials/2026-11-19-feature-requests.md`.

## Out of scope

The `FeatureRequest` model and views (design phase 3), the assistant, FR-4 (a warning on the
admin save of a past opening date: a separate UI change), FR-6 beyond the pickers Part B touches,
FR-7 to FR-16.

## How to work

- Subagents: Sonnet implements, Opus reviews read-only, Sonnet fixes. Part A and Part B are
  separate rounds. Give agents this file's path rather than restating it.
- Conventional commits ending with the Co-Authored-By trailer. Comments state only a non-obvious
  why, in about 3 lines. User-facing strings in Swedish and English.

## Practical notes

- Tests, one suite at a time (they share the test DB and clash in parallel), `uv run` required:
  - `podman exec tryggare_web_1 uv run python manage.py test events registrations --noinput`
  - `podman exec tryggare_web_1 uv run pytest tests/unit/`
  - Frontend: vitest and svelte-check in `tryggare_frontend_1`; the host has no node_modules.
  - Also `ruff check`, `ruff format --check`, `check_messages.py` (run it in the container; the
    host lacks `xgettext`).
- A migration (Part B) needs `makemigrations` in the container; no image rebuild unless a
  dependency changes (then `podman compose up -d --force-recreate --build` and `make wait-dev`).
- Dev runs with `DEMO_MODE=true`: an hourly job reseeds demo data. Admin login `admin` /
  `admin123`; the trial used an Administratör account made with `accounts.roles.grant`.
- To check the admin UI in a browser: Playwright's bundled Chromium doesn't start on this NixOS
  host; the trial drove a Nix-provided Chromium over CDP.
- Push (only when asked): `git -c credential.helper= -c credential.helper='!gh auth
  git-credential' push -u origin <branch>`.
- Local `main` has diverged from `origin/main` (3 local commits, missing the #27 merge). Diff
  against `origin/main`.

At the end, report commits, test counts and anything left open.
