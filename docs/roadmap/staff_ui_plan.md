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

0. **Admin triage pass (~2–3 days).** Columns, filters, search, hide 11 models,
   complete the Swedish catalog, de-leak help text. *Re-estimated up from ~1 day
   by D4 — Django admin is now customer-facing.*
1. **`change_attendee_ticket_type()` service (~1 day).** Domain work, not UI.
1.5. **Roles and permissions (~1–2 days).** *Added by D1.* Three seeded groups,
   real permission classes replacing flat `IsAuthenticated`. No new UI, no schema
   change — and it must precede step 2.
2. **Then one new screen: the Event workspace (attendee roster).**
3. **A money tab on that same screen.**
4. Defer event/ticket setup, logistics counts, and the rest.

**Roughly 4–6 days of no-new-UI work before the first new screen** — up from the
2 days originally drafted. All of the increase comes from decisions D1 and D4,
not from scope creep in the analysis.

Steps 0 and 1 come first not because they are cheap but because **they are the
measurement instrument.** Re-run the persona test after step 0 and the residual
failures are the real, structural ones that justify new UI. Today you cannot
tell "admin is the wrong shape" apart from "admin was never configured" — and
the evidence points mostly at the latter.

**Read this together with the Decisions section at the end** — it is settled, not
open, and it moves three things above: step 0 is bigger (Django admin is
customer-facing after all), there is a new step 1.5 for roles, and step 2 is
bigger (mobile-first at ~600 people, and two roster endpoints rather than one).

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
`registrations.RegistrationExtra`. Add `site_header` / `index_title` and reorder
apps so Events/Registrations sit above Imports/Printing.

> **Superseded by D4: `auth.Group` was on this hide list and comes off it.** It is
> the role-management surface under D1 and must stay visible, well-labelled, and
> translated. Hiding it would remove the only way an org composes a custom role.

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

### Step 1.5 — Roles and permissions (~1–2 days, no new UI)

Added by D1. Must precede step 2, because the roster's *endpoint shape* depends
on it — D1a makes the volunteer roster a separate view, and that is not a
retrofit.

1. **Seed the three groups** (D1) as a data migration with explicit permission
   sets. Reversible; an org's edits must survive re-running it.
2. **Replace flat `IsAuthenticated`.** Every DRF endpoint currently uses the
   default (`config/settings/base.py:161`) or a bare `IsAuthenticated` — see the
   ~20 call sites in `events/`, `families/`, `checkins/`, `reports/`,
   `printing/`, `registrations/`. Each gets a real `DjangoModelPermissions`-based
   class. `imports/views.py` already uses `IsAdminUser` and can stay.
3. **Add the missing `/reports` guard** — there is none today (see D1's
   ground-truth correction). This is a live gap, not new-feature work.
4. **Stop overloading `is_staff` in the frontend.** It currently means both "can
   reach Django admin" and "is a privileged app user". Under D4 it keeps only the
   first meaning; app-tier gating moves to permissions returned by the session
   endpoint. Touches `routes/+layout.ts`, `+page.svelte:60`, `import/+layout.ts`,
   `TopNav`.
5. **`/checkin` health fields become read-behind-reveal for volunteers** (D1b),
   writing the audit row per reveal. **No payment changes** — D1c leaves the
   door money actions alone.

Test obligation: a volunteer-role integration test per restricted endpoint
asserting 403, plus one asserting the volunteer roster payload **does not contain
a balance key at all**. The second is the one that catches a regression D1a was
chosen to prevent.

### Step 2 — Event workspace (first new screen) — `/events/[id]`
One page, three tabs, server-driven, permission-gated (D1), online-only (D5).

**Two roster endpoints, not one** (D1a). `GET /api/events/<id>/roster/` is the
coordinator view; the volunteer view is a separate endpoint whose queryset never
selects balance. One Svelte screen renders both — it shows the columns the
payload actually contains rather than branching on role, so the frontend has no
second copy to drift and no permission logic of its own.
**Roster**: one card/row per attendee — name, age, family, ticket type,
registration status, balance, checked-in, allergy/consent flag; debounced
server-side search across child *and* family name; filter by ticket type and
status; expands to a detail panel with the actions. **Money** (step 3).
**Setup** (deferred; links to admin initially).

Why first: every job starts with "find this person on this event". It reuses
`ExpandableListTable`, `StatusBadge`, `StickySearchBox`, `PageHeader` from
`lib/components/ui/`, and check-in already proved the interaction (inline staff
action → service endpoint → audit → optimistic update).

**Sized larger than originally drafted, because of D2 and D3.** Do not carry the
"one screen, reuse the check-in pattern" estimate forward — two things changed:

- **Mobile-first, not mobile-friendly (D3).** The 390px card is the primary
  artifact and gets built first; the desktop table is the enhancement. Nine
  fields do not fit a phone card, so the card must decide a visual hierarchy —
  name + age + ticket type + status badge visible, the rest behind the expand.
  Measure at 390px before anything else in every critique round.
- **Server-side search and pagination are prerequisites (D2), not follow-ups.**
  The `/checkin` client-side-filter interaction does **not** transfer at 600
  people.

Backend work it needs:

- A new paginated, server-side-searched `GET /api/events/<id>/roster/`, plus a
  default `PAGE_SIZE` in `REST_FRAMEWORK` (there is none today, anywhere). Do
  **not** reach for `/families/`: `FamilyViewSet` has **no `search_fields`** (so
  the already-written-but-unused `familyApi.search()` silently returns
  everything) and returns every family with four nested prefetches. Fine at 9
  families; at D2's 200 it hurts.
- Surface `TicketType.name` in the serializers, and **rename the colliding
  field**: `ChildSerializer.ticket_type` (`'event'|'session'|'none'`) should
  become `ticket_scope`, freeing `ticket_type` to mean the `TicketType`. Do this
  before two screens depend on the ambiguity.

Critique-loop task for this increment: the same failed job, same persona, **on a
390px viewport**. Pass = under 3 minutes, no cross-referencing.

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

## Decisions — settled 2026-08-13 (Johan)

These were the open questions. They are now answered; the plan above and the
increments below assume them.

**D1 — Three seeded roles, built on Django groups. Superseded the first answer.**
*(D1 was briefly "`is_staff` only, no new roles". Reversed the same session — the
product is deployed per-organization and real orgs have volunteers. The reversal
is recorded because the rest of the plan was drafted under the old answer.)*

Three groups, seeded as a data migration:

| Group | App access | Django admin | Money | Health text |
|---|---|---|---|---|
| **Volontär** | check-in, restricted roster | no | door actions only (D1c) | reveal-with-audit, no edit |
| **Koordinator** | everything in the app | no | full | full |
| **Administratör** | everything in the app | yes, scoped (D4) | full | full |

**No schema change is needed.** `AdminUser` already carries `PermissionsMixin`
(`accounts/models.py:34`), so Django groups and per-model permissions work today.
"Custom ACL" is Django Groups — an org that wants a fourth role gets one composed
in admin, not code. Per-event roles remain out of scope: the deployment is
per-organization, so org-level groups are the whole story.

Three sub-decisions carry most of the weight:

- **D1a — Restriction is a separate endpoint, not a filtered payload.** *(Johan's
  answer, better than any option offered.)* The volunteer roster is its own
  view whose queryset never selects balance. The sensitive fields are not
  fetched-then-stripped, so there is no serializer declaration to forget. Model-level
  Django permissions decide which endpoint you can reach; **no field-level
  permission framework is built.**
- **D1b — Health text: reveal-with-audit, not hidden.** A door volunteer is the
  person who most needs to know about a peanut allergy. Volunteers see a "has
  safety info" flag and can reveal the text, writing a `qr_safety_info_revealed`
  audit row — the pattern `qr_reveal_safety_info` already established. Volunteers
  cannot *edit* health fields; `/checkin`'s inline family edit must become
  read-behind-reveal for them.
- **D1c — Volunteers keep the door money actions.** §9.3's inline mark-paid and
  confirm-despite-balance stay available to volunteers, so **`/checkin` needs no
  payment changes at all.** The line is between *handling the family standing in
  front of you* and *browsing everyone's finances* — the latter is what the
  restricted roster withholds.

**Ground-truth correction this exposed:** the original "Auth and roles" open
question (now replaced by this section) claimed the frontend gates `/reports`,
`/import` and the admin link on `is_staff`. That is wrong about `/reports` — `frontend/src/routes/reports/` has **no `+layout.ts`
and no `+page.ts`, so no guard at all.** Any authenticated user reaches it today.
A volunteer tier therefore requires *adding* a `/reports` guard, not adjusting
one. There are also three de-facto tiers today, not two: `AllowAny`,
`IsAuthenticated`, and `IsAdminUser` (all of `imports/views.py`).

**D2 — Scale: plan for ~200 families / ~600 people.**
This makes **server-side search and pagination a step-2 prerequisite, not
cleanup.** Client-side filtering (the `/checkin` pattern) does not carry to this
screen. `GET /api/events/<id>/roster/` ships paginated and server-searched from
its first commit, and `REST_FRAMEWORK` gets a default page size at the same time.

**D3 — Roster device: phone on the floor *and* desk, equally.**
Card-per-attendee at 390px is the primary design; the dense table is the desktop
enhancement, not the other way round. This is the single largest cost change to
step 2 versus the original estimate. Round 3 of the frontend loop already
demonstrated that 390px is precisely where signal strength silently degrades
(a danger border measured byte-identical to a healthy field), so **every step-2
critique pass measures at 390px first.**

**D4 — Tenant admins DO get Django admin, scoped by group, not superuser.**
*(Also reversed the same session. The first answer was "ours only"; custom roles
made that untenable — an org composing its own roles needs somewhere to do it,
and building an in-app role-management screen to avoid handing over a screen that
already exists is not a good trade.)*

`is_superuser` stays ours. The **Administratör** group is `is_staff=True` plus an
explicit permission set — Django admin honours per-model permissions, so the
scoping is configuration, not code:

- **Tenant admin gets**: events, ticket types, extras, registrations, payments,
  families, and **DSAR export/erasure** — they must be able to serve their own
  GDPR requests without us becoming the bottleneck on a statutory deadline.
- **Tenant admin does not get**: printer token rotation (a security operation),
  audit-log deletion (the record that protects both parties), and `AdminUser`
  superuser promotion.

**This reverses the cost of step 0.** Django admin is now a customer-facing
surface, so step 0 is a product commitment, not tidying: the Swedish `.po`
catalog must be *complete*, help text must be operator-grade, and the sidebar
pruning is a UX deliverable. **Budget 2–3 days, not 1.**

It also reverses one specific instruction in step 0C below: **do not hide
`auth.Group`.** It was on the hide list; under D1 it is the role-management
surface and must stay visible and well-labelled.

**D5 — Offline: still online-only.**
No caching, no service worker, no queued writes. The roster is a plain
server-driven page. Accepted exposure: a wifi dropout at a camp kills the roster
mid-shift — the same exposure `/checkin` already carries today. If a camp with
bad wifi ever bites, offline becomes its own roadmap doc and blocks nothing.

**D6 — Meals stay pre-checked; the *bill* gets loud.**
`Extra.default_selected` on "Måltider hela helgen" is correct — most families do
want meals, and flipping it would degrade the kitchen counts (J6). The defect is
that adding a person silently adds 300 kr. Fix is frontend-only: the running
total gets a per-person meal line of its own, so the increment is visible at the
moment it happens. No config change, no backend change.

**D7 — Parent "Relation" default: leave it.** Nothing in the domain branches on
relation. Closed, not deferred.

D6 and D7 are *guest*-side, not staff — they were decided in the same session and
are recorded here so the decision isn't lost, but they belong to the next guest
registration increment, not to any step below.

**D8 — Sequence: step 0 and step 1 together (~2 days), then re-run the persona
test unchanged.** Both are no-new-UI. The re-run is what sizes step 2 honestly.

### Resolved as a consequence, not asked

- **Who the persona represented** — answered by D1's reversal: **both**, and they
  are now different roles seeing different payloads from one screen. The persona
  in the evidence section had admin rights, so it was playing Administratör.
  Design for the coordinator's density, delivered at the volunteer's screen
  width (D3).
- **Print/label ownership** — stays on the QR page. The roster does not get a
  reprint action in step 2. Revisit if the re-run persona reaches for it.

### Still genuinely open

- The re-run persona's residual failures (by construction — that is the point of
  D8). Nothing downstream of step 2 should be estimated until they exist.

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
