# Staff UI plan

Written 2026-08-13, from a live persona test of the current staff surface plus a
read of the models, services and `event_registration_ux_case_catalog.md` §9.
This plan largely *finishes §9* rather than inventing a new staff UI.

## Verdict

**Do not rebuild the staff side. The first move is not new UI at all.**

All three tasks in the live test failed or nearly failed for reasons that are, in
the code, one-line-to-one-day fixes: a missing `list_display` column, a missing
`list_filter`, an uncompiled translation catalog, an unpruned sidebar, and leaked
developer help text.

The one task that failed outright (wrong ticket type) also failed for a second,
deeper reason no UI can paper over: **the safe operation does not exist in the
domain layer.** Changing `EventTicket.ticket_type` in admin today silently
desyncs `price_at_registration` and the `Payment` amount, and nothing validates
that the new type even belongs to the same event. A prettier screen on top of
that ships the same bug with better typography.

Ranked plan:

0. **Admin triage pass (~1 day).** Columns, filters, search, hide 12 models,
   compile the Swedish catalog, de-leak help text.
1. **`change_attendee_ticket_type()` service (~1 day).** Domain work, not UI.
2. **Then one new screen: the Event workspace (attendee roster).**
3. **A money tab on that same screen.**
4. Defer event/ticket setup, logistics counts, and the rest.

Steps 0 and 1 come first not because they are cheap but because **they are the
measurement instrument.** Re-run the persona test after step 0 and the residual
failures are the real, structural ones that justify new UI. Today you cannot
tell "admin is the wrong shape" apart from "admin was never configured" — and
the evidence points mostly at the latter.

## The evidence

A context-free agent playing a church camp coordinator (spreadsheet-comfortable,
not a developer, 30 minutes) was given admin access and three ordinary jobs. It
finished one.

1. *"A family says their 13-year-old is on the 0-12 ticket. Fix it."* —
   **Abandoned.** Nothing lets you search a child by name and see age and current
   ticket together. It opened Children (ages visible only as raw birthdates),
   then opened Event Tickets one at a time, spent 20+ minutes cross-referencing,
   and concluded no 13-year-old existed. Its real-world fallback: email the
   family back and ask for a reference code.
2. *"Create 'Ledare junior', born 2005-2010, 500 kr."* — Completed, with struggle.
3. *"Someone says they paid but shows as unpaid."* — Completed **by guessing**:
   the only outstanding balance belonged to a *different event*, and it marked
   that one paid anyway. An unreviewed database write on a hunch.

Its verdict on the surface: Swedish labels mixed with English model names,
developer help text shown to a volunteer, a sidebar listing every table —
"constant low-grade confusion about which of ~15 similarly-named models held the
answer to a simple question."

## Ground truth

**Django admin** — 26 `ModelAdmin`s across 8 apps plus `auth.Group`, no
`site_header`, no app ordering. Includes a model marked DEPRECATED in its own
docstring (`events.Ticket`), the MTI base that duplicates its two subclasses
(`families.Attendee`), and `ExtraChoice`, registered *only* so
`RegistrationExtraAdmin` can use `autocomplete_fields` — its docstring says so.

**SvelteKit staff surfaces that already work:** `/checkin` (WebSocket-live,
client-side family search including child names, inline family edit, inline
ticket assignment, inline mark-paid / confirm-despite-balance at the door),
`/checkout`, `/print-queue`, `/call-list`, `/qr/[token]`, `/reports` (view-only),
`/import`.

**The precedent to copy:** `/api/registrations/<id>/mark-paid/` is a
staff-authenticated endpoint calling a service function
(`registrations/services.py::mark_payment_paid`), writing `log_audit`, driven
from the check-in screen. Every new staff screen should follow that shape.

## The jobs staff actually do

Ranked by frequency × pain.

### J1 — Find a person and see their whole situation *(the failed task)*
Needs in one place: child's name, age **as a number**, family, event, ticket type
(the `TicketType` name), registration status, outstanding balance, check-in
status, allergy/consent flag.

Fails today because that row exists nowhere. `ChildAdmin` shows a raw
`birthdate` and no ticket. `EventTicketAdmin.list_display = ("attendee",
"event", "id")` — no `ticket_type` column at all. The API is no better:
`Attendee.get_ticket_details()` never surfaces `TicketType`. And there is a
**vocabulary collision**: the API's `ticket_type` means `'event' | 'session' |
'none'`, while the `TicketType` model means "Barn 0-12, 500 kr". Two different
things, same name, both visible to staff.

### J2 — Reconcile a payment *(completed by guessing)*
Needs: per event, every registration with a non-zero balance — reference code,
family, amount, balance, days outstanding — plus record-payment (full / partial /
refund / adjustment) and confirm-despite-balance, audited.

`PaymentAdmin.list_filter = ("status", "method")` — **no event filter.**
`search_fields` is reference code and email only. `balance` is a computed
property: not sortable, not filterable, one extra aggregate query per row. So
"outstanding balances for Sommarläger 2026" is not expressible — which is exactly
why the tester marked the wrong event's registration paid.
`payment_processing.md` already names this gap.

### J3 — Registration triage
`pending_review` (verified email matches a guardian on a *different* family),
duplicates, typo'd contact email, guardian cancellation, expired-unpaid sweeps.
Actions exist (`resolve_pending_review`, `cancel_registrations`); the
queue-shaped view does not. Merge (§9.1) has neither service nor UI.

### J4 — Event, ticket and extras setup *(completed, with struggle)*
Admin models this correctly (`TicketTypeAdminForm` validates session bundles and
cross-event references; `duplicate_extra_to_event` has a custom action). The
struggle is presentational: age tiers are entered as `min_birthdate` /
`max_birthdate` (staff think in ages), ticket types live on a different
changelist from the event, and ten flat columns are shown at once.

### J5 — Check-in day operations
Largely done and good. Residual gap: **activating a session is admin-only**
(`SessionAdmin` checkbox, or the unused `/sessions/<id>/activate/` endpoint) — a
day-of-event action a volunteer needs at 08:55, hidden in a Django form.

### J6 — Logistics and reporting
Case catalog §9.2: kitchen counts by meal/session, T-shirt counts by size, bus
manifest. `Extra` / `ExtraChoice` / `RegistrationExtra` were modeled queryably
*specifically* so this is answerable — and nobody wrote the query. Also
`/reports` renders a snapshot but **cannot generate one**: generation is an admin
action on `EventAdmin`, so a volunteer must leave the app to trigger it.

### J7 — Consent and GDPR duty
`gdpr_compliance.md` names the gap: no staff-facing banner surfacing children in
`needs_reconfirmation`, so the quarantine is silent rather than actionable.
DSAR export/erase are admin actions and should stay there.

### J8 — System configuration
Printers and revocable tokens, import sources, admin users, audit log. Rare,
technical, correctly in admin.

## Where the line falls

### Stays in Django admin — permanently, and say so in the docs
Rare + structural + technical + destructive, already audited: `accounts.AdminUser`,
`auth.Group`, permissions; `printing.Printer` / `PrintJob` (token rotation is a
security operation); `imports.*` sources; `checkins.AuditLog` (read-only
forensic record); `families.Family` DSAR export / erasure (irreversible,
deliberately friction-ful); `registrations.PaymentEvent` (append-only ledger);
`reports.EventReport` rows, `events.PromoCode`, `Extra` / `ExtraChoice` lineage.

Rationale worth writing down: admin is good at *rare structural editing by
someone who understands the schema*. Nothing above is done under time pressure
by a volunteer.

### Moves to purpose-built UI — in this order
1. Attendee roster / find-a-person (J1) — highest frequency, worst current fit
2. Outstanding balances / record payment (J2) — a real correctness hazard today
3. Registration triage queue (J3)
4. Report generation button + extras/logistics counts (J6) — small, high-gratitude
5. Event setup wizard (J4) — last; admin already gets this materially right

### Cheap admin fixes that buy most of the value

**A. Make J1's *find* half work — `events/admin.py`, ~30 lines**

```python
# EventTicketAdmin / SessionTicketAdmin
list_display = ("attendee", "family", "age_at_event", "event", "ticket_type",
                "registration_status", "external_ticket_code")
list_filter  = ("event", "ticket_type")          # ticket_type is missing entirely today
search_fields = ("attendee__first_name", "attendee__last_name",
                 "attendee__family__last_name", "external_ticket_code")
list_select_related = ("attendee", "attendee__family", "event", "ticket_type", "registration")
```

`age_at_event` is an `@admin.display` computing years from `birthdate` against
`event.start_date` — `reports/services.py::_age_on` already does this; reuse it.
This one changeset turns the abandoned 20-minute cross-reference into one search
box and one glance.

**B. Make J2 possible — `registrations/admin.py`**

Add `registration__event` to `PaymentAdmin.list_filter` (the missing piece), add
`registration__family__last_name` to `search_fields`, and annotate the balance in
`get_queryset` instead of computing it per row. Annotating also makes it
**sortable**, which is the actual job ("who owes money, biggest first"). Keep
`Payment.balance` as the single source of truth and assert the annotation matches
it in a test.

**C. Cut the sidebar from 27 entries to ~13.** `get_model_perms()` returning `{}`
hides a model from the index *while keeping autocomplete working*. Apply to
`events.Ticket` (deprecated), `families.Attendee` (MTI base — its rows are the
Children and Parents listed directly above), `events.ExtraChoice`,
`checkins.CheckInRecord`, `imports.FestivalProImportSource`, `printing.PrintJob`,
`registrations.RegistrationExtra`, `auth.Group`. Add `site_header` /
`index_title` and reorder apps so Events/Registrations sit above Imports/Printing.

**D. Fix the bilingual mess — but diagnose it correctly first.** The mixed-language
admin is real: `LocaleMiddleware` reads the `django_language=sv` cookie *the
frontend language switcher sets* (`frontend/src/lib/i18n/i18n.ts:67`), so
Django's own chrome renders in Swedish ("Lägg till", "Spara", "Ändra") while the
model labels come back English.

The first draft of this plan blamed a missing build step. That is **wrong** —
both `backend/Dockerfile:33` and `backend/Dockerfile.prod:72` run
`django-admin compilemessages`. The actual cause is narrower: `docker-compose.yml`
bind-mounts `./backend:/app`, which **shadows the image-built
`locale/sv/LC_MESSAGES/django.mo` with the host directory that only has
`django.po`**. So the symptom is dev-only, and the persona hit it because the
persona tested dev.

Two things still need doing regardless:

1. `locale/sv/LC_MESSAGES/django.po` carries 48 msgids and is missing roughly 26
   model verbose names, so even a correctly compiled catalog leaves much of the
   admin English. Finish the catalog.
2. Add a `check:messages` CI guard mirroring `check:tokens`, so a stale catalog
   fails the build rather than silently degrading.

For dev specifically, either run `compilemessages` on the host after editing the
`.po`, or drop the `.mo` out of the bind-mounted path. Verify the *prod-like*
build before concluding anything about production: this symptom does not
reproduce there.

**E. De-leak the developer help text.** Rendered to volunteers verbatim today:
`TicketType.capacity` ("Schema placeholder only — not yet enforced anywhere…"),
`TicketType.is_active` ("…see on_delete=PROTECT on EventTicket/SessionTicket"),
`EventTicket.ticket_type` ("…Phase 3+"), `EventTicket.price_at_registration`
("Snapshotted once at submission — never recomputed…"). Move the rationale to the
model docstring and leave `help_text` as one operator-facing sentence. Case
catalog §9.4 actively wants the reassuring version of the snapshot note
("editing a price is safe — sold tickets keep their price"), in human words.

## Sequenced plan

### Step 0 — Admin triage (~1 day, no new UI)
Fixes A–E. Unblocks J2 (no more guessing), makes J1's find half work, stops the
surface insulting the reader. **Then re-run the persona test unchanged.**
Whatever still fails is the real backlog, measured rather than assumed. Do not
skip this measurement.

### Step 1 — `change_attendee_ticket_type()` service (~1 day, no new UI)
In `registrations/services.py`, alongside `record_payment_event`. Must: validate
the new `TicketType` belongs to the same event; validate against
`min_birthdate` / `max_birthdate` (**warn, don't block** — case catalog §2.2, the
birthday-crossing child, requires a staff override); write a `PaymentEvent`
`ADJUSTMENT` for the price delta rather than mutating `price_at_registration`
(snapshot at write time, never recompute); `log_audit`. Ship it as an admin
intermediate-page action first, reusing the `duplicate_extra_to_event` pattern
and template.

**The single highest-value change in the plan.** It converts the failed task from
impossible-and-unsafe into two clicks, and any UI claiming to fix a ticket needs
it anyway.

Also here: an `is_active=False` guard so retired ticket types stop appearing, and
an assertion that `EventTicket.ticket_type.event_id == EventTicket.event_id` —
nothing enforces this today, and admin will happily attach another event's type.

### Step 2 — Event workspace (first new screen) — `/events/[id]`
One page, three tabs, server-driven. **Roster**: one row per attendee — name,
age, family, ticket type, registration status, balance, checked-in,
allergy/consent flag; search-as-you-type across child *and* family name; filter
by ticket type and status; row expands to a detail panel with the actions.
**Money** (step 3). **Setup** (deferred; links to admin initially).

Why first: every job starts with "find this person on this event". It reuses
`ExpandableListTable`, `StatusBadge`, `StickySearchBox`, `PageHeader` from
`lib/components/ui/`, and check-in already proved the interaction (inline staff
action → service endpoint → audit → optimistic update).

Backend work it needs:

- A new paginated, server-side-searched `GET /api/events/<id>/roster/`. Do **not**
  reach for `/families/`: `FamilyViewSet` has **no `search_fields`** (so the
  already-written-but-unused `familyApi.search()` silently returns everything),
  **no pagination configured anywhere in `REST_FRAMEWORK`**, and returns every
  family with four nested prefetches. Fine at 9 families; a 400-family camp hurts.
- Surface `TicketType.name` in the serializers, and **rename the colliding
  field**: `ChildSerializer.ticket_type` (`'event'|'session'|'none'`) should
  become `ticket_scope`, freeing `ticket_type` to mean the `TicketType`. Do this
  before two screens depend on the ambiguity.

Critique-loop task for this increment: the same failed job, same persona. Pass =
under 3 minutes, no cross-referencing.

### Step 3 — Money tab
Outstanding balances for this event sorted by balance; record payment (full /
partial / refund / adjustment) inline; confirm-despite-balance with the audit
note. Reuses `mark_payment_paid` / `record_payment_event` unchanged — already
correct and well-tested. Critique task: "Someone says they paid but shows unpaid."

### Step 4 — Small wins, any order, half a day each
- **"Generate report" button** on `/reports` — calls `generate_event_report`,
  removes an admin round-trip from a screen that otherwise never needs one.
- **Session activate/deactivate** from the check-in header — endpoints exist.
- **Extras/logistics counts** on the workspace (§9.2) — pure aggregation over
  `RegistrationExtra`. "Middag lördag: 74 bekräftade + 6 obetalda."
- **`needs_reconfirmation` banner** (J7) — closes a named GDPR gap.

### Step 5 — Deferred, deliberately
Event/ticket setup wizard (admin does this correctly and the task *passed*);
family merge (§9.1 — build `merge_families()` as a management command + admin
action when needed, UI much later); registration triage screen
(`RegistrationAdmin` is the least-bad admin surface in the repo); any offline /
PWA work.

## Open questions — for a human, not an agent

**Auth and roles — the biggest one.** `accounts.AdminUser` has `is_active`,
`is_staff`, `is_superuser` plus `PermissionsMixin` (Django groups/permissions
exist, unused). Every DRF endpoint is flat `IsAuthenticated`; the frontend gates
`/reports`, `/import` and the admin link on `is_staff` alone. Two accidental
tiers, no modeled roles — and admin requires `is_staff`, so **the test persona
had staff or superuser rights.**

- Is there a real tier below "staff" — a check-in volunteer who should see the
  roster but never a balance or an allergy field?
- Should the event workspace be `is_staff`-only, or does a coordinator without
  admin access need it? (If the latter, the workspace becomes the *whole* answer
  for them and its priority rises sharply.)
- Are there per-event roles? Nothing supports that today; it is a schema change.

**Phone or laptop during check-in?** The spec says "optimized for laptop,
mobile-friendly". Is the roster used *on the floor* on a phone, or at a desk?
Decides table-vs-card and how much the design can lean on horizontal space.

**Offline.** The spec says "No offline capability. If network fails, all access
is lost." Still true, or has a camp with bad wifi changed it? Must be answered
before step 2 — a roster with local caching is a different project.

**Scale.** Live dev data is 9 families / 14 children / 3 events. Is a realistic
camp 50 families or 500? How many staff hit check-in at once? Decides whether the
missing pagination is cleanup or a blocker.

**Who did the persona represent?** A one-off volunteer at the door, or the
coordinator who configured the event weeks earlier? They want different products:
three big buttons versus a dense table.

**Is Django admin an operator-facing feature of the hosted product?**
`docs/legal/DPA_NOTE.md` and the Tryggare Moln docs describe a SaaS offering with
live pilots. If tenant admins get admin access, hardening it is a product
commitment, and step 0 changes from "cheap fix" to "must be excellent".

**Print/label ownership.** Does the roster need a reprint action, or does that
stay on the QR page?

## Cross-cutting constraints

**Children's data and consent.** The roster must render allergy/notes as a *flag*
("has safety info") with the text behind an explicit reveal, mirroring
`qr_reveal_safety_info`, which writes a separate `qr_safety_info_revealed` audit
entry per reveal so a glance is distinguishable from an access.
`FamilyViewSet.retrieve` similarly logs `record_viewed`. **Any new roster
endpoint returning health text must log at the same granularity, or it becomes
the quiet hole in an otherwise careful audit trail.** Health text must never join
the extras/logistics export (§9.2 states this). `Parent` also carries health
fields now — do not build a child-only mental model.

**Bilingual EN+SV, same change.** ~651 keys each in
`frontend/src/lib/i18n/locales/{en,sv}.json`. On the backend, step 0's
`compilemessages` fix is a prerequisite for admin work to be bilingual at all.

**Design system.** No hard-coded colors/radii/shadows; `rounded-button` for
controls, `rounded-card` for containers, `--radius-lg` is marketing-only. Green
is reserved for trust/success/live — an "unpaid" row is `warning`/`danger`, and
"paid" is the only thing that earns green. No emoji; `✓ ✗ →` and stroke-only
Lucide icons at width 2. `npm run check:tokens` is CI-enforced.

**WebSockets.** Check-in, checkout, print queue and call list subscribe to
`child_checked_in` / `child_checked_out` / `checkin_undone` / `checkout_undone`.
The roster shows check-in state, so it should subscribe too — and any *new*
message type must not break the printer client, which authenticates with a
per-printer token via `config/ws_auth.py::PrinterTokenMiddleware`.

**Backend dev loop.** Daphne imports Python once; backend changes need
`date > restart-dev.txt` and ~10s. Ruff format + check gate CI. `manage.py test`
does not discover `backend/tests/unit/` — run `uv run pytest tests/unit/` too.

## Critical files

- `backend/events/admin.py` — step 0's biggest win; also where the leaked help text surfaces
- `backend/registrations/admin.py` — the missing `registration__event` filter, the balance annotation
- `backend/registrations/services.py` — where `change_attendee_ticket_type()` belongs
- `backend/families/serializers.py` — the `ticket_type` naming collision; source of the roster payload
- `frontend/src/routes/checkin/+page.svelte` — the working precedent `/events/[id]` should copy
- `docs/roadmap/event_registration_ux_case_catalog.md` §9 — the staff-side spec this plan finishes
