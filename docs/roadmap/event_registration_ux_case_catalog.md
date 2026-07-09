# Event Registration — Deep-Detail Case Catalog & UX Flow

## Status (2026-07-08)

Design document, nothing here is built. This is the deep-detail companion to
[event_registration_and_mailing.md](event_registration_and_mailing.md) —
specifically to its "Phases 3-6" section, which sketched `TicketType`,
`Extra`, `RegistrationExtra`, `RegistrationAccessToken`, `PromoCode` and
`RegistrationGroup`. This document pressure-tests that sketch against an
exhaustive case catalog and a start-to-finish UX walkthrough, and ends with
a punch list of model changes the sketch is missing. The punch list is the
part meant to be folded back into the roadmap doc.

Ground truth referenced throughout:

- `registrations/models.py` — `Registration` (status machine, 48h
  verification TTL, 7-day payment TTL, `created_new_family`, materialized
  immediately at submission), `Payment` (OneToOne, manual Swish/Bankgiro
  reconciliation, all-or-nothing `refunded` status).
- `events/models.py` — `Event` (single `price`, no capacity, no
  registration window), `Session` (no capacity), `EventTicket` /
  `SessionTicket` (`unique_together` on attendee+event / attendee+session).
- `families/models.py` — `Attendee` MTI base; `allergies` / `notes` /
  `health_consent_*` live **only on `Child`**; `Parent` has
  email/phone/relationship_type and no health fields at all.
- `checkins/eligibility.py::registration_checkin_gate_error` — a ticket
  only counts once `registration.status == confirmed`.
- The `imports/` app's FestivalPro/Planning Center lessons: positional
  prefix mapping ("Barn 3" + document-order field matching) and
  adult-inferred-by-email-presence are the two ambiguity patterns that
  caused real bugs. The self-serve form must never *infer* structure —
  every attendee is explicitly typed, every field explicitly attached to a
  person, every extra explicitly attached to a scope.

Two recurring design principles fall out of the catalog below; naming them
once up front so the individual cases can just reference them:

- **P1 — Explicit structure over inference.** Direct inversion of the
  import-pipeline pain. Nothing about an attendee, price, or extra is ever
  derived from position, field presence, or string matching.
- **P2 — Snapshot at write time, never recompute.** Prices, ticket-type
  assignment, consent notice versions: decided and frozen at the moment
  the guardian commits them. Staff editing event configuration afterwards
  must be *safe by construction* because nothing confirmed re-derives.

---

# Part 1 — Case catalog

## 1. Capacity & availability

### 1.1 There is no capacity model at all today

**Scenario.** A summer camp has 120 beds. The current model has no field
anywhere that says so — `Event`, `Session`, and the Phase 3 `TicketType` /
`Extra` sketches are all uncapped. The first real camp on self-serve
registration will oversell silently.

**Why tricky.** Capacity isn't one number. Real events cap at (at least)
three levels simultaneously: whole event (beds), per session (the Saturday
canoe trip takes 30), and per ticket type (only 40 "with lodging" tickets,
unlimited day visitors). And capacity interacts with the status machine:
does a `pending_verification` registration hold a seat? A
`pending_payment` one? Get this wrong in either direction and you either
oversell (confirmed family turned away — reputational disaster for a
church) or let spam submissions DoS a popular event.

**Real-world.** Eventbrite holds inventory during an active checkout for
~20 minutes and releases on abandonment — right idea, but their scale
problem isn't ours. Planning Center Registrations does per-attendee-type
and per-signup-time capacity well and is the closest analogue. FestivalPro
lets organizers oversell by editing counts mid-sale with no protection.
Cvent does per-session capacity with agenda conflict detection — correct
but administratively heavy.

**Recommendation.** Add nullable `capacity` (PositiveInteger, null =
unlimited) to `Event`, `Session`, and `TicketType`. One accounting rule,
one place (`registrations/capacity.py`): **a seat is held by any ticket
whose registration is not `cancelled`** — i.e. `pending_verification`,
`pending_payment`, `pending_review`, and `confirmed` all count. Holding
during `pending_verification` is deliberate: the 48h TTL sweep already
bounds how long spam can squat a seat, the `(event, contact_email)` dedup
bounds how many seats one actor can squat, and the alternative
(only-confirmed counts) guarantees overselling on any event that fills in
under 48 hours. Do **not** build a separate reservation/hold system — the
Registration lifecycle already *is* one, TTLs included.

### 1.2 Overbooking under concurrent submissions

**Scenario.** 118 of 120 seats taken. Two families, four seats total,
submit within the same second. Both count-then-insert checks pass; the
event is at 122.

**Why tricky.** Classic TOCTOU. The naive serializer-level
`count() < capacity` check is exactly wrong under concurrency, and this
*will* happen: Swedish church camps genuinely fill in minutes when
registration opens (announced in a service, whole congregation opens the
link at 12:00).

**Recommendation.** Inside the existing submission transaction,
`select_for_update()` the `Event` row (and any capacity-bearing `Session`
/ `TicketType` rows, always locked in a fixed pk order to avoid
deadlocks), recount, then insert. At church scale — tens of concurrent
submissions, not tens of thousands — Postgres row locks on the event row
are completely sufficient. Do not reach for Redis reservations, advisory
locks, or a queueing layer; that's solving Ticketmaster's problem, not
ours. The lock is held for milliseconds (materialization is a handful of
inserts).

### 1.3 Sold out mid-form

**Scenario.** A guardian opens the form when 3 seats remain, spends 12
minutes filling in three children (toddler on hip, see Part 2), and the
seats are gone at submit.

**Why tricky.** The temptation is to reserve seats when the form *opens*.
That converts every drive-by page view into a capacity hold and requires
the hold/expiry machinery case 1.1 just declined to build. But telling
someone "sold out" *after* 12 minutes of typing allergies is the single
most rage-inducing outcome the form can produce.

**Real-world.** Eventbrite reserves at checkout-start — works, costs them
the hold machinery. TicketTailor checks at submit and shows a sold-out
error — cheap and infuriating. Planning Center shows live counts but
doesn't reserve until submit.

**Recommendation.** Three-layer mitigation instead of holds: (a) the
landing page shows coarse availability ("Gott om platser" / "Få platser
kvar" / "Fullt") so expectations are set before typing starts; (b) the
form re-checks availability via a cheap endpoint when the guardian
reaches the review step — catching the race *before* the consent/health
step, not after; (c) if submit still loses the race, the error page
converts directly into the waitlist join (case 1.4) with everything
already typed carried over — name(s) and contact email pre-filled from
the form state. The guardian's 12 minutes are never discarded.

### 1.4 Waitlist

**Scenario.** Event full. Ten families want in. Two confirmed families
cancel in week 3. Who gets the seats, how are they told, how long do they
get, and what data did we hold about them meanwhile?

**Why tricky.** A waitlist is a queue with seat-count-shaped entries (a
family of 5 can't take 2 freed seats), an offer protocol with expiry, and
— specific to this system — a GDPR question: a waitlist entry is personal
data held about people who may *never* attend, so it must hold the
minimum and expire aggressively. Also: the waitlist must not silently
bypass capacity — the offer link has to *reserve* the freed seats or the
next public visitor races the offeree.

**Real-world.** Eventbrite's waitlist (timed claim window, auto-release,
next-in-line) is the right protocol shape. Planning Center's is similar.
Most church-world tools (Realm) have none, and staff run waitlists in a
spreadsheet — which is exactly what pilot congregations will do to us if
we don't build it, and their spreadsheet will contain health data.

**Recommendation.** New model, deliberately thin:

```python
class WaitlistEntry(models.Model):
    event = FK(Event)
    session = FK(Session, null=True)        # null = whole-event waitlist
    ticket_type = FK(TicketType, null=True) # null = any type
    contact_email = EmailField()
    seats_needed = PositiveIntegerField(default=1)
    display_name = CharField()              # "Familjen Lindqvist" — no attendee rows
    status = CharField(choices=["waiting", "offered", "converted", "expired", "withdrawn"])
    offer_token_hash = CharField(blank=True)
    offer_expires_at = DateTimeField(null=True)
    created_at = DateTimeField(auto_now_add=True)
```

No children's names, no birthdates, no health data — you do not need
allergies to stand in a queue (data minimization, and it keeps
special-category data out of a table the compliance machinery doesn't
cover). On a seat freeing: offer to the **first entry whose
`seats_needed` fits**, not strictly FIFO — but the head-of-queue larger
party keeps its position for the next opening (skipped, not demoted).
State that policy in the UI; silent skip-ahead generates support email.
The offer is a magic link (same token shape as everything else) valid 48h
that opens the registration form with the seats held by a
`pending_verification`-equivalent hold (reuse: the offer itself can
create nothing; the *form submission* through an offer-token URL is
allowed to exceed public capacity by exactly `seats_needed`). Waitlist
entries hard-delete at event end.

### 1.5 Extra stock sells out mid-period (T-shirt sizes)

**Scenario.** 50 camp T-shirts ordered: 10 S, 20 M, 15 L, 5 XL. XL is
gone by week 2 of a six-week registration window.

**Why tricky.** In the Phase 3 sketch, `Extra.choices` is a JSON list of
strings. Stock lives at the *choice* level, not the extra level — a JSON
string list can't carry a count, a sold counter, or a per-choice price.
And stock decrement has the same concurrency problem as 1.2 but on a
different row.

**Real-world.** Eventbrite models merch variants as separate ticket
add-ons each with own quantity — clunky but sound. RegFox does
conditional form fields with no stock concept at all; organizers oversell
shirts every season and eat the reorder cost.

**Recommendation.** Promote choices out of JSON into a real model — this
is punch-list item #2 and it fixes three cases at once (stock here,
per-choice pricing in 3.2, referential integrity in 9.4):

```python
class ExtraChoice(models.Model):
    extra = FK(Extra, related_name="choice_rows")
    label = CharField()                 # "XL"
    price_delta = DecimalField(default=0)
    stock = PositiveIntegerField(null=True)   # null = unlimited
    sort_order = IntegerField(default=0)
    is_active = BooleanField(default=True)    # soft-retire, never delete

# RegistrationExtra.choice_value: CharField  →  choice = FK(ExtraChoice, null=True)
```

Stock accounting uses the same not-cancelled rule and the same
`select_for_update` discipline as 1.1/1.2 — one mechanism, documented
once. UX: a sold-out choice renders disabled with "Slutsåld", never
hidden (hidden options make guardians think the form is broken).

### 1.6 Editing a confirmed registration against a full event

**Scenario.** A confirmed family uses their Phase 4 full-scope link to
add a fourth child. The event filled up last week.

**Why tricky.** Phase 4's edit design says nothing about capacity. If
edits bypass the capacity check, the waitlist is a lie; if they don't,
the edit flow needs the same sold-out/waitlist UX as the public form.

**Recommendation.** Edits go through the same capacity service as
submissions — one code path (`capacity.py`), no exceptions. Adding an
attendee to a full event offers the waitlist for that one attendee.
Removing an attendee frees seats and triggers waitlist processing
exactly like a cancellation. Staff-side edits get an explicit override
("register anyway, exceed capacity") with an audit log entry — staff
*should* be able to oversell deliberately (the pastor's family always
fits), the public never.

## 2. Pricing & tickets

### 2.1 Tickets with food vs. without food

**Scenario.** Leaders' conference: 800 kr with meals, 500 kr without.
Three candidate models: (a) a boolean toggle on the ticket, (b) a
per-attendee priced `Extra` ("Måltider, 300 kr"), (c) two `TicketType`
rows ("Konferens med mat", "Konferens utan mat").

**Why tricky.** This is the archetype for a whole class of decisions, so
the reasoning matters more than the instance. Option (c) —
ticket-type variants — is the trap: it *works* for one axis, then the
event adds lodging (×2), then early-bird (×2), and staff are maintaining
"Youth early-bird with food without lodging" among 16 ticket types, and
the kitchen can't get a headcount without summing across 8 of them.
FestivalPro events end up exactly there, and the import pipeline has the
scar tissue to prove it. Option (a) — a bespoke boolean — solves food
and nothing else, and food is not special.

**Real-world.** Planning Center's per-attendee "selections" (add-ons
asked per person) is the good pattern. Eventbrite pushes organizers
toward ticket-variant explosion because add-ons came late to their model;
their organizers' stats pages are unusable for catering counts.

**Recommendation.** **(b), the per-attendee `Extra`, is correct.** One
extra row "Måltider hela helgen, 300 kr", `per_attendee=True`. Kitchen
headcount = `RegistrationExtra` count for that extra — one query. Every
future axis (lodging, linen rental, bus transfer) is another extra, not a
multiplication. The ticket price is the *base admission*; extras are
everything separable. Two carve-outs: (1) if food is genuinely
inseparable from the ticket (a gala dinner *is* the event), price it into
the ticket and don't model food at all; (2) if the organizer wants
food-included as the default with an opt-*out* discount, model it as the
extra pre-checked by default (`Extra.default_selected = BooleanField`) —
never as a negative-priced extra, which wrecks itemized receipts and
promo math.

### 2.2 Age-tiered pricing and the birthday-crossing child

**Scenario.** Pricing: 0-12 barn 400 kr, 13-17 ungdom 700 kr, vuxen
1 100 kr. Ebba is 12 at registration in March, turns 13 in May, camp is
in July. Which price?

**Why tricky.** Three defensible answers (age at registration, age at
event start, age at event end) and the *worst* outcome is not picking one
— then it's decided per-support-email. Worse, the recompute trap: if
ticket price derives live from birthdate, a staff member correcting a
typo'd birthdate silently reprices a confirmed, paid registration (P2
violation).

**Real-world.** Airlines: age at travel date, stated at booking — the
right shape. CampMinder/UltraCamp price by *school grade*, not age,
because grade is stable across a booking season — smart in the US where
school-year cutoffs split calendar years. Sweden makes this easy:
Swedish school cohorts follow calendar birth year (you start school the
year you turn six), so "årskurs 4-6" *is exactly* "born 2014-2016" — a
birthdate window subsumes grade tiers with zero extra modeling.

**Recommendation.** Extend the Phase 3 `TicketType` with
`min_birthdate` / `max_birthdate` (nullable dates). Staff can enter them
directly ("born 2013-2019", i.e. a cohort/årskurs window) or the admin UI
computes them from "age 7-12 **at event start**". The rule, printed on
the form: *price is based on age on the event's first day*. Ebba is 13 on
day one of camp → ungdom, 700 kr, decided and **snapshotted at
submission** (`price_at_registration` plus the `ticket_type` FK, both
already in the sketch). Her birthday, a later birthdate correction, or a
staff price change never reprices her ticket; if a birthdate *typo*
correction means she was mis-tiered, that's a staff-initiated ticket-type
change through the edit flow (case 8.2), visible and audited — not a
silent recompute.

### 2.3 Early-bird pricing and the verification gap

**Scenario.** Early-bird ends June 1 at 23:59. A family submits at 23:50,
clicks the verification email at 00:15 June 2. Which price? Second order:
their `pending_payment` registration expires after the 7-day TTL and they
re-register June 10.

**Why tricky.** Every price boundary creates a fencepost dispute, and
"submitted vs. verified vs. paid" gives three fenceposts. The roadmap
already says early-bird is a `TicketType` validity window, not a promo
code — right call, but the window needs schema (it's prose-only in the
sketch) and a decided fencepost.

**Recommendation.** Add `available_from` / `available_until` (nullable
datetimes) to `TicketType`. The fencepost is **submission time** — the
moment of materialization, which is also when the price snapshot is
taken, so it falls out of P2 for free. Verification lag never changes
price. The re-registration case: they pay the June price. Correct and
non-negotiable at the model layer — the escape hatch is human, not
mechanical: staff issue a fixed-amount `PromoCode` (max_uses=1) to comp
the difference. Do not build "honor the old price on re-registration"
logic; it's a dedup nightmare and the promo escape hatch costs staff 30
seconds.

### 2.4 Mixed ticketing: EventTicket plus paid add-on sessions

**Scenario.** Youth conference: full-event pass 900 kr, plus an optional
Saturday climbing excursion, 150 kr, capacity 20 — *on top of* the full
pass. Today an `EventTicket` semantically covers all sessions, so "a
session that costs extra even for pass-holders" contradicts the model's
core invariant.

**Why tricky.** Two representations compete. As a `SessionTicket` with
its own `TicketType`: but the attendee already holds an `EventTicket`,
and check-in logic treats EventTicket as covering every session — the
excursion session would appear free to the eligibility gate. As a
session-scoped `Extra`: money and headcount are right, but extras don't
gate check-in.

**Recommendation.** Decide by one question: **does staff scan for it at
a door?** If the session needs its own admission control (limited-seat
excursion where gate-crashing matters), model it as a Session with
`requires_ticket=True` that is **excluded from EventTicket coverage** —
add `Session.included_in_event_ticket = BooleanField(default=True)`; the
check-in eligibility gate and the registration form both read it.
Pass-holders buy a real `SessionTicket` (with `ticket_type`, priced,
capacity-counted) for it. If nobody scans (Saturday dinner — kitchen
just needs a count), it's a session-scoped `Extra` (case 3.1) and the
ticket model stays out of it. Both mechanisms exist anyway; the flag is
the only new schema.

### 2.5 Zero-priced ticket types and the `Event.is_paid` trap

**Scenario.** "Volunteer/ledare — 0 kr" ticket type on an otherwise paid
event. Or a family whose entire itemized total is 0 (two leader tickets).

**Why tricky.** Today paid-ness is `Event.price is not None and > 0`, and
the status machine branches on it (`confirmed` vs `pending_payment`).
With Phase 3 itemization, paid-ness is a property of *this registration's
total*, not the event. A 0 kr total routed to `pending_payment` creates a
Payment row of 0 that staff must "mark paid" against a bank statement
line that will never arrive — a guaranteed stuck registration.

**Recommendation.** The verification branch becomes: `total == 0 →
CONFIRMED`, `total > 0 → PENDING_PAYMENT`. `Event.price` stays only as
the Phase 0-2 fallback for events with no ticket types defined.
`registrations/pricing.py::calculate_total` is the single source of
truth; nothing else re-derives paid-ness.

### 2.6 Multi-day events, partial attendance

**Scenario.** A three-day family camp. One family comes Friday-Sunday;
a grandmother joins Saturday only; a family attends days but sleeps at
home (no lodging).

**Why tricky.** The current shape — `EventTicket` = everything,
`SessionTicket` = exactly one session — has no middle. "Saturday only"
means hand-picking every Saturday session, which is both tedious UX and
wrong pricing (a day rate isn't the sum of session rates). The
import-pipeline precedent looms: FestivalPro models day-passes as string
ticket names parsed by convention — do not.

**Recommendation.** Model days as Sessions (one Session per day for
camp-shaped events — the check-in system already thinks in sessions),
and give `TicketType` an explicit coverage:

```python
# TicketType gains:
    kind = CharField(choices=["event", "session_bundle"], default="event")
    sessions = M2M(Session, blank=True)   # only for session_bundle
```

An `event`-kind type materializes an `EventTicket`; a `session_bundle`
type ("Lördagspass, 350 kr") materializes one `SessionTicket` per listed
session, all sharing the one `ticket_type` FK and one price snapshot
(price on the *bundle*, not per session — store the snapshot on each
SessionTicket row but sum it only once via the ticket_type grouping, or
simpler: snapshot the full bundle price on the first row and 0 on the
rest is a hack — instead add the line-item concept from case 5.2 and hang
the price there). Capacity: a bundle consumes capacity in each covered
session. Lodging is an `Extra`, not a ticket dimension (per 2.1).

### 2.7 Price display, VAT, and öre

**Scenario.** Does the receipt need VAT lines? Can a price be 99,50 kr?

**Why tricky.** Only because getting it wrong looks amateurish on a
receipt. Swedish ideella föreningar (the entire customer base) are
almost universally not moms-registered for member activities — no VAT
line, and *showing* one would be wrong.

**Recommendation.** No tax modeling. Flat SEK amounts, `DecimalField`
stays (Swish handles öre), but recommend whole-krona prices in admin
help text — every real church price list is whole kronor, and öre
amounts make manual bank-statement reconciliation (the actual payment
rail) needlessly error-prone. Receipts say "Momsfri verksamhet" nowhere
— silence is correct; don't volunteer tax language.

## 3. Extras & add-ons

### 3.1 Session-scoped extras — the flagged model gap

**Scenario.** Saturday-evening festmiddag (150 kr, kitchen cap 80) on a
three-day event. A workshop materials fee that only makes sense for
people attending that workshop's session. Today's Phase 3 `Extra` is
event-scoped only — the commissioner's explicit question.

**Why tricky.** Without session scoping you get two failure modes seen
in real tools: (a) the extra is offered to everyone including Sunday-only
attendees, who buy dinner for an evening they won't be there (RegFox
forms do this constantly — the form doesn't know what the ticket covers);
(b) organizers fake it with naming conventions ("Middag LÖRDAG — endast
för er som är där på lördag!!") — inference-by-string, the exact
FestivalPro disease (P1 violation). There's also a lifecycle coupling:
if an edit removes the Saturday day-pass, the Saturday dinner extra is
now orphaned — attached to an attendee who won't be in the building.

**Recommendation.** Punch-list item #1:

```python
# Extra gains:
    session = FK(Session, null=True, blank=True)  # null = event-wide
    applies_to = CharField(choices=["parent", "child", "either"], default="either")
```

Validity rule, enforced in the service layer (it's cross-table, so no DB
constraint): a session-scoped extra may only attach to an attendee whose
tickets cover that session (`EventTicket`, or a `SessionTicket`/bundle
including it, respecting 2.4's `included_in_event_ticket`). The edit
flow enforces the converse: removing session coverage from an attendee
lists their now-invalid extras and requires explicit confirmation to
drop them (with refund delta per 5.2) — never silent cascade-delete of
something the guardian paid for. `applies_to` comes along in the same
change because it solves 2.1's residual problem (child-priced meals:
"Måltider barn 200 kr" `applies_to=child`, "Måltider vuxen 300 kr"
`applies_to=parent`) with zero new mechanism.

### 3.2 Extras needing captured information vs. pure toggles

**Scenario.** Four flavors in the wild: (a) yes/no toggle (bus transfer),
(b) choice from a list (T-shirt size, cabin preference, which of three
workshops), (c) quantity (2 parking passes), (d) free text ("describe
your dietary requirements").

**Why tricky.** Flavor (d) is a GDPR landmine dressed as a form field.
Dietary free text is health data (allergies) and/or religious data (halal,
kosher) — Art. 9 special categories both — and the Phase 3 sketch would
store it in `RegistrationExtra.choice_value`, a plain CharField with **no
consent versioning, no notice, no export/erase integration, outside the
`Child.save()` consent backstop**. Every serious platform gets this
wrong: Eventbrite, RegFox, and FestivalPro all offer free-text custom
questions, organizers all use them for dietary/medical info, and that
data then lives in CSV exports forever. This system's entire value
proposition is *not* doing that.

**Recommendation.** Hard position: **free-text extras do not exist in
this system.** `Extra` supports exactly three input shapes: toggle
(no choices), single choice (`ExtraChoice` rows, case 1.5), and quantity
(`RegistrationExtra.quantity`, new field, for `per_attendee=False`
extras only). Anything health-, diet-, or accessibility-shaped is
captured in the *dedicated, consent-gated* fields (existing
`Child.allergies` + the new attendee-level fields from case 10.1) which
carry notice versions and flow through export/erase. The dinner extra's
choice list can carry structured options ("Vegetarisk", "Vegansk",
"Glutenfri" — dietary *choice* offered by the kitchen, not disclosed
health condition); the free-text "other allergies" prompt next to it
links into the health-consent block instead. Add
`Extra.required = BooleanField` for must-choose-one cases
(accommodation: tält/stuga/bor hemma) — renders as radio, not checkbox.

### 3.3 Per-registration extras and quantity

**Scenario.** A shared cabin (one per family), a parking pass (a family
might want two), a program booklet (one per family, free).

**Why tricky.** `per_attendee=False` exists in the sketch but with no
quantity, "two parking passes" needs two `RegistrationExtra` rows for
the same extra with `attendee=None` — which the natural unique constraint
would forbid, and which staff reports would double-count ambiguously.

**Recommendation.** `RegistrationExtra.quantity =
PositiveIntegerField(default=1)`, only >1 allowed when
`per_attendee=False`. Unique constraint `(registration, extra, attendee)`
so a per-attendee extra can't be double-attached (the two-tab case 4.4
protection at the row level). Price = `quantity × (extra.price +
choice.price_delta)`, snapshotted.

### 3.4 Extras gated by ticket type

**Scenario.** Lodging extra should only be offered to full-event
tickets; the day-visitor bundle shouldn't see it.

**Why tricky.** Legitimate need, but every gating dimension added to
`Extra` multiplies form logic and admin UI complexity. The session FK
(3.1) plus `applies_to` (3.1) already covers the large majority: lodging
is naturally "event-wide extra" whose absurdity for day visitors is
mostly theoretical (a day visitor buying a bed is odd but not harmful —
they paid for a bed).

**Recommendation.** Explicitly **defer**. Do not add
`Extra.ticket_types` M2M in Phase 3. Session scoping and `applies_to`
land first; if a pilot congregation hits a real (not aesthetic) case that
those can't express, the M2M is a small additive migration. Recording the
deferral here so it's a decision, not an oversight.

## 4. People & relationships

### 4.1 Returning family — prefill without a login

**Scenario.** The Lindqvists registered for last year's camp. This year
they face a blank form: two parents, three children, birthdates,
allergies, all from scratch. On a phone. Meanwhile the system *has* all
of it, and re-entry doesn't just cost time — it creates a duplicate
`Family` with duplicate `Attendee` rows, splitting the check-in history
and doubling the GDPR surface.

**Why tricky.** No persistent login exists *by design* (the roadmap's
explicit, correct decision), so recognition has to work another way. And
prefill is a data-exposure question: typing an email into a public form
must never *display* another family's data — that would let anyone
enumerate families by guessing emails. The existing `pending_review`
mechanism already embodies the right instinct (email matching an
existing guardian on a different family → staff review, not auto-attach)
but it's reactive; returning families need it proactive.

**Real-world.** Realm/Church Center prefill from the member household
database — but only behind their login, and their duplicate-household
mess when a spouse uses a different email is legendary among church
admins. Eventbrite's "checkout autofill" is browser-level only.
UltraCamp does returning-family login with full health-form carryover
and an explicit "review and re-confirm health info yearly" step — the
best pattern in the field, minus the account requirement.

**Recommendation.** Email-first form (Part 2, step 1). On blur/continue,
the server answers only **"fresh start" or "check your inbox"** — never
any data. If the email matches an existing `Parent.email`, send a magic
link (one-time token, same shape as everything else); the link opens the
form **prefilled with names and birthdates** of that parent's family.
Health data is *not* injected into form fields even post-link — instead
the child's step shows "Vi har hälsoinformation om Ebba sedan tidigare"
with a view/confirm/update interaction (see Part 2 step 4); the
inbox-control proof makes *showing* it acceptable (same trust level as
`/qr/[token]`), and "stämmer det fortfarande?" doubles as consent
re-confirmation with a fresh notice version. Materialization then
**reuses** the existing `Family`/`Attendee` rows (`created_new_family =
False` — the field and its sweep-protection semantics already exist for
exactly this), so no duplicates are born. A guardian who ignores the
"check your inbox" path and just fills the form fresh falls through to
today's `pending_review` — the reactive net stays as backstop.

### 4.2 The child who aged out since last year

**Scenario.** Prefill (4.1) offers the Lindqvist children; Hugo is now
18. He's a `Child` row in an MTI table, but this year he's an adult
attendee — possibly a leader.

**Why tricky.** MTI makes "change subclass" a row-surgery operation, not
a field update: `Parent` and `Child` are separate tables sharing the
`Attendee` pk. Doing it ad-hoc in a request handler risks
half-migrated rows; *not* doing it means an adult carries
`Child.health_consent_status` semantics (guardian-attested consent for a
person who is now his own data subject — legally wrong, not just untidy).
The memory note about stale downcast refs after the Parent/Child rename
is a warning shot from this exact terrain.

**Recommendation.** A dedicated, transactional, audit-logged service:
`families/services.py::promote_child_to_parent(child)` — inserts the
`parents` row for the same attendee pk, migrates nothing health-shaped
(his allergies re-enter under *his own* consent per 10.1, the old
child-record consent doesn't transfer — the attestation basis changed),
deletes the `children` row. The registration form triggers it lazily: a
prefill-offered child who is ≥18 at event start renders as "Hugo, 18 —
registrera som vuxen", and acceptance calls the service at
materialization. Never auto-run it in a sweep; the family decides when
Hugo is an adult attendee.

### 4.3 Group leader / bulk registration — registrant ≠ consent holder

**Scenario.** A youth leader registers 20 kids from the congregation for
a summer festival. The leader knows names and rough ages, pays with the
congregation's card, and **cannot lawfully attest health consent for
children who are not theirs** — Art. 9(2)(a) consent comes from the data
subject's guardian, full stop. The leader also should not be typing
allergies from memory (wrong attestor *and* wrong data — a double fault).

**Why tricky.** Three roles that the current model collapses into one:
registrant-of-record (the leader — owns the booking, pays), payer (the
congregation), and consent-holder-of-record (each child's guardian —
twenty different people). Also a structural mismatch: `Registration` ↔
`Family` is 1:1 and *correct* (roadmap Phase 6 decision — check-in and
pickup semantics), so 20 unrelated kids cannot pile into the leader's
`Family` without destroying pickup-authorization semantics.

**Real-world.** CampMinder/UltraCamp nail the *sequencing*: enrollment
(who's coming, who pays) is separate from the health form, which is a
post-registration workflow completed later by each guardian against a
deadline, with staff dashboards showing completion. That's the pattern
to steal. Planning Center lets one person register many with all
questions inline — which forces exactly the leader-types-allergies
failure. FestivalPro's group bookings infer adulthood from email
presence; enough said.

**Recommendation.** The bulk flow is **Phase 6's `RegistrationGroup`
wearing a different UI** — no new payment machinery:

- The leader flow captures, per child: name, birthdate, **guardian name +
  guardian email/phone**. Nothing else. The flow contains **no health
  fields at all** — structurally absent, not merely discouraged.
- Materialization creates one minimal `Family` per child (child + their
  actual guardian as `Parent`), one `Registration` per family, all in one
  `RegistrationGroup` with the leader as group contact and one `Payment`
  on the group (exactly the Phase 6 shape — this unification is the
  strongest argument for building Phase 6 at all, and it upgrades Phase
  6's priority from "last, rarest case" to "carries the bulk flow").
- Each guardian gets an email: "Ledaren Anna har anmält Ebba till
  Festivalen — komplettera hälsoinformation här", carrying a
  guardian-scoped magic link (the Phase 4 `self` scope pointed at the
  child's registration covers this; if scope semantics get fuzzy, add an
  explicit `guardian` scope — same table). The guardian completes
  health info + consent under their own attestation, or explicitly
  declines ("ingen hälsoinformation").
- Tickets are valid immediately (the leader knows who's coming); missing
  health completion does **not** block check-in — consent gates *storing
  health data*, not attendance, which is the existing semantic. Staff
  get a completion dashboard ("14 av 20 vårdnadshavare klara") and a
  reminder-email button; the leader's group link shows the same counts
  without the health content itself.

### 4.4 Duplicate and near-duplicate submissions

**Scenario.** (a) Mom double-taps submit / has the form open in two
tabs. (b) Mom and dad each register the family, days apart, from
different emails. (c) Two families genuinely share a child's name and
birthdate — or the same family typos "Elsa" vs "Elsa " vs "elsa".

**Why tricky.** Three different problems wearing one name. (a) is an
idempotency bug; (b) is a semantic duplicate invisible to the existing
`(event, contact_email)` dedup because the emails differ; (c) is why
hard-blocking on name matches is wrong (å/ä/ö normalization, trailing
whitespace, common names — and any hard block becomes a support ticket
with a distressed guardian). The import pipeline's duplicate-key JSON
lesson applies: ambiguous identity matching must degrade to *human*
review, never to silent merge or silent rejection.

**Recommendation.** Three layered mechanisms, matched to the three
problems: (1) an **idempotency key** — a UUID minted client-side when
the form initializes, submitted with the POST, unique-indexed on
`Registration`; a retry/double-tap/second-tab replay returns the
existing registration instead of creating a sibling. (2) The existing
`(event, contact_email)` dedup, unchanged. (3) A **soft post-materialization
sweep**: on verification, match this registration's children against
other non-cancelled registrations on the same event by
(normalized first_name, birthdate); a hit routes to the existing
`pending_review` staff queue with both registrations linked — staff
resolve with the merge tooling (9.1). Never auto-merge, never block.

### 4.5 Two families co-registering and splitting payment

**Scenario.** The Bergs and the Ekmans book a retreat together and want
one checkout — or want to split it 60/40.

**Recommendation.** Phase 6 already decided the structure (two
`Registration` rows, one `RegistrationGroup`, one `Payment`) and it's
right. On *splitting*: **don't build it.** The payment rails are manual
Swish/Bankgiro against a bank statement; "split payment" in Swedish
social reality is one person pays and the other Swishes them half —
that transaction is none of this system's business. Supported shapes:
one group + one payer, or two independent registrations each paying
their own. A split-payment ledger across manual rails is reconciliation
hell for staff (two partial payments to match against one group) for
zero real need.

### 4.6 Blended families, shared custody, and the non-guardian adult

**Scenario.** A child alternates weeks between two households; both
want registration/pickup rights. Or a grandmother registers and attends
with the grandkids. Or the "Parent" on the booking is mom's partner,
not a legal guardian.

**Why tricky.** `Child` has exactly one `Family` FK, and `Parent`
means "adult attendee of the household", not "legal guardian" —
`relationship_type` is a free string. For registration this mostly
works; the sharp edge is *consent attestation*: a grandmother may
register and pay, but health-data consent should come from a guardian.
Fully modeling Swedish custody arrangements is a rabbit hole
(vårdnadshavare records, dual-household children) that even dedicated
school systems handle badly.

**Recommendation.** Don't model custody. Do two small honest things:
(1) the consent block's attestation text says what's being claimed —
"Jag är vårdnadshavare för Ebba, eller har vårdnadshavarens uppdrag att
lämna dessa uppgifter" — so the legal basis is what the attestor
affirmed, recorded with notice version as today; (2) the second-household
case is handled by 4.1's returning-family path plus the `pending_review`
queue when the other household's email surfaces — staff decide whether
to merge or keep two households (sometimes two households is *correct*).
Note in staff docs that pickup authorization stays a check-in-time
concern, out of registration's scope.

### 4.7 No personnummer — data minimization as a feature

**Scenario.** Swedish digital forms reflexively demand personnummer.
Some staff will ask for it ("all the other systems have it").

**Recommendation.** Hard no, permanently. Birthdate serves pricing
(2.2) and identification-at-scale isn't a requirement — check-in works
on family + name + ticket. Personnummer would upgrade every breach,
export, and retention question for zero functional gain, and its absence
is a *selling point* to privacy-literate congregations. Record the
refusal here so it doesn't get relitigated per-customer.

## 5. Payment & money

### 5.1 Partial cancellation and partial refunds

**Scenario.** Confirmed and paid: 2 vuxna + 2 barn + extras, 3 400 kr.
One child breaks an arm two weeks out; the family cancels that child
(700 kr ticket + 300 kr extras). They're owed 1 000 kr — or less per the
refund policy.

**Why tricky.** `Payment.status` is all-or-nothing (`paid` /
`refunded`), which cannot represent "paid 3 400, refunded 1 000, net
2 400". And because rails are manual, the system doesn't *execute*
refunds — staff Swish the money back — so the model's job is to
**record** money movements accurately enough that the balance is always
derivable, not to move money.

**Real-world.** Eventbrite/Cvent have full refund engines tied to their
gateways — irrelevant machinery here. Small tools (TicketTailor) track
partial refunds as ledger lines against the order — the right shape at
the right weight.

**Recommendation.** Punch-list item: an append-only ledger, and
`Payment` becomes a summary over it:

```python
class PaymentEvent(models.Model):
    payment = FK(Payment, related_name="events")
    kind = CharField(choices=["received", "refunded", "adjustment"])
    amount = DecimalField()          # signed by kind, always positive here
    note = CharField(blank=True)     # "Swish-återbetalning, Ebba avanmäld"
    created_by = FK("accounts.AdminUser", null=True)
    created_at = DateTimeField(auto_now_add=True)
```

`Payment.amount` becomes "current amount owed" (recomputed from the
registration's line items on each edit — the *owed* side may change;
the *received* side is ledger-only). Balance = owed − received +
refunded. `Payment.status` derives: `pending` (balance > 0, nothing
received), `paid` (balance ≤ 0), `partially_paid` (new status: something
received, balance > 0). This one ledger also carries under/overpayment
(5.3) and edit-repricing (8.2) — one mechanism, three cases.

### 5.2 Line items — the missing spine under all money cases

**Scenario.** Every case above keeps needing "the itemized total" as a
first-class thing: 5.1 needs to know what the cancelled child's slice
was; 8.2 needs deltas; receipts need lines.

**Why tricky.** The Phase 3 sketch scatters price snapshots across
`EventTicket.price_at_registration`, `SessionTicket.price_at_registration`,
and `RegistrationExtra.price_at_registration`, then sums them in
`pricing.py`. Workable — until the day-bundle (2.6) needs one price
across N SessionTickets, a promo discount (5.4) needs to appear on the
receipt as a line, and a removed attendee's history needs to survive the
ticket row's deletion.

**Recommendation.** Keep the scattered snapshots (they're good
denormalization and Phase 3 can ship with them alone), but plan the
receipt/delta layer as a *rendering* over them plus two additions:
promo discount recorded on `Registration`
(`promo_code FK` + `discount_amount` snapshot — see 5.4), and cancelled
line preservation: **soft-delete tickets/extras removed by edits**
(`removed_at` timestamp) instead of row deletion, so refund math and
receipts have history. Registration-owned rows already hard-delete via
the TTL sweep for *unverified* registrations — that stays; soft-delete
applies only to edits of verified ones.

### 5.3 Underpayment, overpayment, and unmatchable payments

**Scenario.** Registration owes 1 500 kr. The bank statement shows
1 200 kr from someone whose Swish message says "läger Ebba o Hugo"
instead of the reference code. Another line says 1 550 kr with the right
code.

**Why tricky.** Manual reconciliation means the payment message is typed
by a human, and humans write children's names, not reference codes. The
memory note on payment verification already surfaced real bugs here.
Staff need to record "received 1 200 against R7K2M9QX" without the
system either auto-confirming (it's short) or rejecting the record.

**Recommendation.** The `PaymentEvent` ledger (5.1) records exactly
what arrived; `partially_paid` status surfaces the 300 kr gap on the
staff dashboard with a one-click "skicka påminnelse om restbelopp"
email. Overpayment shows a negative balance with a "registrera
återbetalning" action. Neither blocks confirmation *if staff say so*:
confirming at `partially_paid` is a staff judgment call (deliberate —
church reality is "they'll pay the rest at camp"), logged. The deeper
fix is upstream: the payment page pre-fills the Swish message with the
reference code via QR (Part 2, step 8), attacking the unmatchable-payment
problem at the source.

### 5.4 Promo codes: stacking, scoping, and hidden ticket types

**Scenario.** (a) A family tries "EARLYBIRD" + "SYSKON10" together.
(b) A code meant to discount only youth tickets discounts the whole
booking. (c) A "VOLONTÄR" code should reveal an otherwise-invisible 0 kr
volunteer ticket type. (d) 50-use code, 3 people redeem the 50th slot
simultaneously.

**Why tricky.** Stacking is a combinatorial pricing bug generator and a
support-email generator (order of application: percent-then-fixed or
fixed-then-percent changes the total). Whole-total codes are wrong the
first time an organizer wants "10% off children's tickets" and the
discount silently eats the adult tickets too. Hidden-type unlock is the
classic staff/volunteer pattern and if unsupported, organizers publish
the volunteer price publicly and beg people not to use it (observed on
real Eventbrite church events).

**Real-world.** Eventbrite: one code per order (right), code-unlocks-
hidden-tickets (right), per-ticket-type scoping (right) — promo codes
are the one thing Eventbrite fully solved; copy them. RegFox allows
stacking and their own docs warn about it.

**Recommendation.** **One code per registration, ever** — a DB-level
single FK (`Registration.promo_code`, null=True), so stacking is
unrepresentable rather than validated away. Add to the Phase 5 sketch:
`PromoCode.applies_to_ticket_types = M2M(TicketType, blank=True)` (empty
= whole itemized total; non-empty = discount computed over matching
ticket lines only), `TicketType.is_hidden = BooleanField(default=False)`,
and `PromoCode.unlocks_ticket_types = M2M(TicketType, blank=True)`.
Discount amount is computed and **snapshotted** as
`Registration.discount_amount` at submission (P2; a staff edit to the
code later never reprices). Usage accounting: count at submission (the
code is consumed by materialization, released by the TTL sweep on
expiry/cancellation — identical semantics to capacity, case 1.1), with
the increment done under the same submission lock
(`select_for_update` on the `PromoCode` row) so the 50th-slot race has
one winner. 100%-discount totals hit the 2.5 rule: total 0 → confirmed,
no Payment row.

### 5.5 Refund cutoffs and cancellation policy

**Scenario.** "Full refund until June 1, 50% until June 15, nothing
after." Guardian cancels June 20 and expects money.

**Why tricky.** The temptation is a rules engine (tiered cutoffs,
percentages, per-ticket-type overrides). But refunds are *executed
manually by humans* here, and Swedish church reality is that the rule
bends the moment the reason is a broken arm — the pastor refunds anyway.
An enforcement engine would be authoritative-looking fiction.

**Recommendation.** Model the *communication*, advise the *decision*:
`Event.refund_cutoff` (nullable date) + `Event.cancellation_policy_text`
(shown on the form before payment and in the confirmation email — this
is also a consumer-information hygiene matter). Guardian-initiated
cancellation after the cutoff still works (tickets release, capacity
frees, waitlist fires) but the staff dashboard tags it "efter
återbetalningsgräns — beslut krävs" and the refund, whatever staff
decide, is recorded as a `PaymentEvent`. No percentage math in code.

### 5.6 The 7-day payment TTL vs. hot events

**Scenario.** A 120-seat camp sells out in a day; 15 registrations sit
`pending_payment` holding seats for up to 7 days; 10 waitlist families
wait.

**Why tricky.** `PAYMENT_TTL_DAYS = 7` was set as a fixed business rule
balancing bank-transfer clearing time against seat-hoarding — correct
for the uncontended case. Under contention every unpaid day is a seat a
waiting family can't have.

**Recommendation.** Keep 7 days fixed (an operator-tunable TTL is a
support foot-gun — the roadmap's "fixed business rule, not
operator-tunable" stance holds). The pressure valve is the reminder
email at day 5 ("betala inom 2 dagar, annars släpps era platser till
kön") — which is honest, motivates payment, and needs building anyway
(7.2). The waitlist absorbs the churn; that's what it's for.

## 6. Consent & legal

### 6.1 Consent granted in January, event in July, expiry in between

**Scenario.** Health consent carries an 18-month validity window.
Consent attested January 2025 expires ~July 2026 — mid-camp. Or a
returning family's consent (4.1) from last season lapses a week before
this year's event.

**Why tricky.** The planned renewal machinery is calendar-driven
(sweep for approaching expiry, send renewal email). But the *operational*
requirement is event-relative: what matters is whether consent is live
**through the event's end date**, and a calendar sweep can fire the
renewal at a moment disconnected from any event, when the guardian has
no reason to care, then not fire again before the moment it matters.

**Recommendation.** Two-part rule. (1) At registration: if the attested
consent would expire before `event.end_date`, the registration flow's
consent step *is* the renewal — a fresh attestation with a fresh notice
version resets the window (4.1's "stämmer det fortfarande?" interaction
does this for free for returning families). (2) Event-aware sweep: at
T−30 days before `event.start_date`, find that event's attendees whose
consent expires before `event.end_date`; send renewal links (existing
planned mechanism, new trigger) and surface the list on the staff event
dashboard. If unrenewed by event start, the existing
`needs_reconfirmation` semantics apply — health data flagged, staff can
re-attest at check-in with the guardian physically present. **Not** a
check-in block: consent gates the health data, never the child's
attendance.

### 6.2 Who attested, exactly — guardian attestation identity

**Scenario.** Staff-attested consent records `health_consent_by` (FK to
`AdminUser`). Guardian self-serve attestation has no AdminUser. Two
years later a DPO question arrives: "who consented to storing Ebba's
allergy data, on what basis, when?"

**Recommendation.** The attestation identity for self-serve consent is
**the verified contact email**, bound through the registration: consent
captured at submission is provisional until email verification succeeds
(which the status machine already enforces — an unverified registration
is swept, consent and all). Store the linkage explicitly:
`health_consent_registration = FK(Registration, null=True)` alongside
the existing `health_consent_by` (exactly one of the two set). The
audit answer becomes: "attested via registration R7K2M9QX, contact
verified as anna@example.se on 2026-03-14, notice v3."

### 6.3 Photo/media consent — the missing consent type

**Scenario.** Every Swedish church camp photographs kids and posts to
the congregation's Instagram. Today that consent is collected on paper,
or not at all. The registration form is the one moment every guardian is
present and attentive.

**Recommendation.** This is the concrete trigger for the roadmap's
"cross-cutting: consent generalization" (`ConsentRecord`) — pull it
forward. Add `photo` to the consent-type choices, capture it as an
optional per-child (and per-adult) toggle in the consent step,
default **unchecked**, entirely decoupled from health consent (a
guardian can grant one and refuse the other, and bundling them would
taint both legally). Expose it in check-in/staff views so leaders can
actually honor it. Do *not* block registration on it — it's orthogonal
to attending.

### 6.4 Minimum registrant age

**Scenario.** A 16-year-old registers herself for a youth conference —
common in reality (the FestivalPro imports are full of self-registered
teens). Swedish dataskyddslagen sets 13 as the age of digital consent,
but Art. 9 health data of a minor is a different matter from ordinary
personal data.

**Recommendation.** V1 hard rule, stated on the form: **the registrant
must be 18+ — a guardian or a leader** (the leader case flowing through
4.3 so consent still reaches the guardian). A 16-year-old's registration
arriving anyway is undetectable (no personnummer, by design — 4.7), so
the rule is an attestation, not a gate, and that's fine: it fixes where
legal responsibility sits. Teen self-registration *without* health data
is a legitimate future relaxation — flag it as a config-level policy
decision per congregation, explicitly not built now.

### 6.5 Erasure and bookkeeping collide

**Scenario.** A family pays, then invokes GDPR erasure before the event.
Bokföringslagen requires the congregation keep accounting records
(receipts, payments) for 7 years — and the payment record references the
registration.

**Recommendation.** The existing `scrub_family` anonymization pattern
extends, it doesn't fork: erasure anonymizes attendee PII (already
built), cancels tickets, but **preserves `Registration` (reference code,
amounts, dates) and `Payment`/`PaymentEvent` rows** — a reference code
plus amounts is the bookkeeping artifact, and with PII scrubbed it no
longer identifies a person. Verify the sweep and `dsar.py` export treat
`RegistrationExtra` rows (which may carry choice FKs but, per 3.2, never
free text) as attendee-adjacent: anonymized attendee → extra rows kept
for finance, attendee FK survives pointing at the anonymized row. Add
`registrations` to the DSAR export scope — a registration *is* personal
data (contact email, what was bought).

### 6.6 Retention of registration data itself

**Scenario.** Camp 2026 ends. When do the registration rows, extras,
and price snapshots die?

**Recommendation.** Two clocks, already the system's idiom: attendee
PII follows the existing participation-based retention/anonymization
sweep (`last_participation_date` machinery — ensure event attendance
via self-serve registration *updates* it); financial skeleton
(Registration reference + amounts + Payment ledger) follows
bokföringslagen's 7 years, held in anonymized form per 6.5. No new
retention setting; wire registration into both existing clocks and
document the mapping in `gdpr_compliance.md`.

## 7. Communication

### 7.1 What the confirmation email must and must not contain

**Scenario.** The confirmation is the artifact families keep, forward
to grandparents, and screenshot into the family group chat. It's also
permanently outside the app's retention pipeline the moment it's sent.

**Why tricky.** The existing rule — no allergy/health text in email
bodies, ever — is enforced *by convention*. Phase 3 adds new fields that
look innocent and aren't: a `RegistrationExtra` for "Middag" with choice
"Glutenfri" is health-adjacent; an accessibility note (10.1) is health
data outright. Convention degrades as fields multiply.

**Recommendation.** MUST contain: event name/dates/place, reference
code, attendee **first names** (utility outweighs sensitivity; no
birthdates), itemized amounts with total and any discount line, payment
instructions + deadline where applicable, the full-scope manage link,
cancellation policy text (5.5), a "vad händer nu" timeline, and an
`.ics` attachment. MUST NOT: allergies/notes, dietary choice values,
accessibility text, birthdates, other families' anything (group
bookings: each family's mail covers their own slice; the leader's mail
has names + completion status only). Upgrade the enforcement from
convention to structure — punch-list item: email templates take a
dedicated `ConfirmationEmailContext` dataclass of whitelisted primitives,
never model instances, so adding a leaky field requires a deliberate
act at the choke point instead of an accidental template reference.
Everything sensitive lives one click away behind the token link, where
it's access-controlled and inside retention.

### 7.2 The email sequence — every mail states the next step and its deadline

**Scenario.** Guardians live in inbox chaos. Each mail must be
self-sufficient: what happened, what happens next, by when, what to do
if nothing happens.

**Recommendation.** Fixed sequence, each with an explicit deadline
sentence: (1) verification mail — "bekräfta inom 48 timmar, annars tas
anmälan bort"; (2) on verify, free events → confirmation (7.1); paid →
payment instructions with the 7-day deadline and Swish QR link;
(3) day-5 payment reminder (5.6) — build it into the existing sweep,
it's a query plus a template; (4) confirmation on payment marked;
(5) T−7 days pre-event practical-info mail (what to bring, times,
address) — staff-authored body, system-sent, because otherwise staff
export emails to BCC from a private Gmail, which is the shadow-IT
failure this product exists to prevent; (6) Phase 4 self-scope links to
other adult attendees, sent **at confirmation** (not submission — don't
notify people about a registration that may evaporate unverified).
All transactional (legitimate interest) — none touch the
marketing-consent track, per the roadmap's two-kinds-of-email rule.

### 7.3 The typo'd email — silent death of a registration

**Scenario.** `anna@gamil.com`. The verification mail bounces or lands
nowhere; 48h later the sweep erases the registration; the family shows
up at camp unregistered and *certain* they registered.

**Why tricky.** From the guardian's perspective the form said "klart!"
and then nothing. No error ever reaches them, by definition. This is a
top-3 support generator on every platform (Eventbrite's help center has
a dedicated article tree for exactly this).

**Recommendation.** Three cheap layers: (1) the post-submit screen
displays the email address back in large type — "Vi har skickat ett mejl
till **anna@gamil.com** — fel adress?" with an inline correct-and-resend
action (new token, old one invalidated; punch-list item since contact
email is currently immutable pre-verification); (2) client-side
common-domain typo hint (gamil/gnail/hotmial → "menade du gmail.com?") —
20 lines of frontend, zero false blocking; (3) if the SMTP relay reports
a hard bounce, surface it on the staff dashboard's pending list rather
than swallowing it — staff often *know* the family and will just call
them.

### 7.4 Bilingual guardians (Swedish/English)

**Scenario.** An international congregation: half the guardians read
Swedish, half English — sometimes within one family.

**Recommendation.** The form gets a sv/en toggle (Django i18n and the
`locale/` scaffolding already exist); the chosen locale is snapshotted
as `Registration.locale` (punch-list item) and drives **every**
subsequent email and token-page render for that registration —
mid-lifecycle language flapping is worse than either language. Event
*content* (ticket type names, extra names, policy text) is **not**
translated by the system: no translation tables in v1; congregations
that care write "Lunch lördag / Saturday lunch" in the name field. This
matches what Eventbrite does and what nobody complains about. Chrome
translated, content verbatim.

## 8. Editing & lifecycle

### 8.1 Who may edit what — the scope matrix

**Scenario.** Phase 4 defines `full` and `self` scopes but not the
field-level matrix, which is where the disputes live: may a self-scoped
adult remove themselves? May the full-scope holder edit another adult's
allergies?

**Recommendation.** The matrix, decided:

| Action | `full` (registrant) | `self` (adult attendee) |
|---|---|---|
| Own contact info | yes | yes |
| Another adult's contact info | yes | no |
| Own dietary-choice extras / own health info | yes* | yes |
| Child health info (child on own family) | yes | yes (if guardian-relation on the family) |
| Add attendee | yes (capacity-checked, 1.6) | no |
| Remove attendee / partial cancel | yes | **self-removal: yes** |
| Change ticket types, event-level extras | yes | own only |
| Apply/replace promo code | yes | no |
| Cancel whole registration | yes | no |
| See payment status/balance | yes | own share not shown — totals are the registrant's business |

*The starred cell is the one deliberate wrinkle: the full-scope holder
may edit health info for children of the registration's family (they're
the attesting guardian), but for *another adult attendee* they may not —
an adult's health data is their own; the self link exists precisely so
Uncle Per manages his own shellfish allergy. Self-removal is allowed
(an adult can always withdraw themselves; forcing them to phone the
registrant is paternalism) and notifies the full-scope holder by email.

### 8.2 Edits that change the amount owed

**Scenario.** Confirmed, paid 3 400 kr. An edit adds an extra (+150),
removes a child (−1 000). New owed: 2 550. Net: 850 kr refund due. Or
the reverse: family owes 150 more.

**Why tricky.** The status machine wants to be reused
(`pending_payment` again?) but that's wrong: bouncing a *confirmed*
registration back to `pending_payment` over 150 kr would re-block
check-in eligibility (the gate keys off status) — locking a family out
of camp over a T-shirt is absurd, and the church context is
trust-based.

**Recommendation.** **Status and balance are orthogonal.** Once
`confirmed`, edits never regress status; they update the owed side of
the `PaymentEvent` ledger (5.1) and the derived balance. Positive
balance → automatic email with the delta, Swish QR for exactly the
difference, reference code as message; staff dashboard shows outstanding
balances per event. Negative → "återbetalning registreras av
personal" surfaced to staff. Pricing of edits follows P2 at line-item
granularity: new items snapshot at *edit-time* prices (adding a child
after early-bird ends costs the current price — automatic, correct, no
special case), existing untouched items keep their original snapshots.
Removed items soft-delete (5.2) so the receipt history explains the
balance.

### 8.3 Edits that change what was consented or verified

**Scenario.** An edit changes the contact email. An edit adds a new
child with allergy text. An edit adds an adult who's never been
notified.

**Recommendation.** Changing contact email through the full-scope link
triggers re-verification of the *new* address (mail to new address with
confirm link; old address gets an FYI — account-takeover hygiene, same
pattern as every account system, no account required). A newly added
child's health block runs the identical consent capture as the main
flow — the edit page reuses `ConsentCapture.svelte`, not a trimmed
variant (trimmed consent forms are how rigor erodes). A newly added
adult triggers their self-scope link mail immediately (they're being
registered *now*; confirmation already happened).

### 8.4 Guardian-initiated cancellation

**Scenario.** Full cancellation via the full-scope link, before or
after payment.

**Recommendation.** Pre-payment: instant — status `cancelled`, tickets
released, capacity freed, waitlist fires (1.4), confirmation email.
Post-payment: same mechanics plus the refund path of 5.5 (recorded by
staff as `PaymentEvent`s, advisory cutoff). One deliberate friction: a
type-to-confirm ("skriv AVBOKA") on whole-registration cancel — this is
a destructive action reachable from a long-lived emailed link that
family members forward around; a single tap is too little ceremony.

### 8.5 Draft vs. materialize-immediately — the honest tension

**Scenario.** A camp form for a family of five is long. The guardian
wants to start on the bus and finish at home. Materialize-immediately —
chosen deliberately so Art. 9 data enters export/erase/audit machinery
at the instant of capture — has no half-submitted state.

**Why tricky.** Every "just add a drafts table" resolution quietly
recreates the problem materialize-immediately was built to kill: a
server-side draft holding allergy text in a JSON blob is
special-category data sitting *outside* the consent-versioning, DSAR
export, erasure, and sweep machinery — or you make drafts fully
compliant, at which point you've re-implemented materialization with a
second lifecycle and doubled the compliance surface. And cross-device
resume requires an emailed magic link, which is ~80% of the friction of
simply submitting.

**Real-world.** UltraCamp solves it with accounts (off the table here,
by design). Eventbrite doesn't solve it (checkout is short).
FestivalPro's long forms just lose people's work — their abandonment
mid-form is part of why churches hate it.

**Recommendation.** Take the position and record it: **no server-side
drafts.** Persistence below the submit line is client-side only —
localStorage autosave keyed per event, so a closed tab, dead battery, or
crashed in-app browser resumes on the same device with "Fortsätt där du
var?" (data never leaves the device before submit — GDPR-clean because
nothing is *processed*). Cross-device resume is explicitly out of scope
for v1. The real mitigation is upstream: make the form short enough
that resume rarely matters (Part 2's whole design; target under 5
minutes for a returning family, under 10 cold). Revisit only if pilot
telemetry shows systematic long-form abandonment — and if that day
comes, the compliant design is "submit early, edit later": materialize
after step 1 with minimal data and let the Phase 4 edit flow *be* the
resume mechanism, rather than building a parallel draft store.

### 8.6 Walk-up / on-site registration through the same pipe

**Scenario.** Camp check-in day; a family arrives unregistered. Staff
must register them on the spot — with the same extras, pricing, and
consent capture — and take Swish payment at a folding table.

**Why tricky.** Staff *can* already create Family + tickets directly
(the pre-registration path), which is exactly the danger: a walk-up
created that way has no `Registration`, no `Payment`, no line items —
it's invisible to event finance, extras headcounts, and the
registration reports. Divergence won't announce itself; it'll surface
as "kitchen count is 4 short" and "kassan stämmer inte".

**Recommendation.** Punch-list item: `Registration.source =
CharField(choices=["self_serve", "staff", "import"])`. The staff
check-in UI gets a "registrera på plats" action that drives the **same
service functions** as the public endpoint
(`create_family_with_members`, same pricing, same consent capture via
the shared `ConsentCapture` component — the guardian is physically
present, so attestation is staff-witnessed-guardian, the strongest
variant) with three sanctioned deviations: no email verification
(status straight to `confirmed`; `contact_email` becomes blankable for
`source=staff` only), payment markable immediately ("betalade med Swish
nu" → `PaymentEvent` on the spot), and the capacity override of 1.6.
The old direct Family-creation path remains for non-registration uses
but event-day staff flow routes through Registration.

### 8.7 Organizer cancels or moves the whole event

**Scenario.** Storm warning; camp cancelled Wednesday before. 87
confirmed registrations, most paid. Or: "we'll move you all to the
August week."

**Recommendation.** Staff bulk action: cancel-event → every
registration to `cancelled`, refund lines pre-drafted in each ledger
(staff confirm as the Swish repayments actually go out — the ledger
tracks reality, per 5.1), and a mass transactional email (this is
transactional, not marketing — contract necessity). Transfers: **don't
build event-transfer.** Cancel + a 100% single-use promo code for the
August event per family is the same outcome with zero new model
surface, and staff understand it. A dedicated transfer feature is an
enterprise-Cvent thing solving volume this product doesn't have.

## 9. Operational / staff-side

### 9.1 The `pending_review` queue and duplicate-family merge

**Scenario.** 4.1's returning-family flow shrinks the queue; 4.4's
soft-dedup sweep feeds it. Staff resolve each with: attach to existing
family, keep separate, or merge two families.

**Recommendation.** Django admin suffices for *viewing* (per the
roadmap's existing deferral) but merge is not an admin-form operation —
it's row surgery across MTI tables, tickets, consents, and check-in
history. Build `families/services.py::merge_families(primary,
duplicate)` as an audited service first (management command +
admin-action wrapper), UI later. Merge rules: union attendees,
keep primary's consent records where both exist (newer notice version
wins), repoint tickets, never merge health text automatically (flag
conflicts for staff eyes).

### 9.2 Logistics reports are the other half of extras

**Scenario.** The kitchen needs meals-per-day by dietary choice; the
T-shirt orderer needs counts by size; the bus coordinator needs a
manifest. If the system can't answer these, staff export CSVs into
Sheets, and the Sheets grow health-adjacent columns (the shadow-IT
failure again).

**Recommendation.** Extras were modeled queryably on purpose — ship the
queries as event-dashboard counts: per `Extra`, per `ExtraChoice`, per
session (session scoping from 3.1 is what makes "middag lördag: 74"
answerable at all), counting only non-cancelled registrations and
flagging pending-payment counts separately ("74 bekräftade + 6
obetalda"). The allergy/health report stays inside the existing
consent-gated staff views — never joined into the extras export.

### 9.3 Unpaid at the door

**Scenario.** Check-in day; a `pending_payment` family is at the front
of the queue. The gate (`registration_checkin_gate_error`) correctly
blocks them. A queue is forming.

**Recommendation.** The check-in screen shows *why* ("obetald anmälan —
1 500 kr") with an inline staff action: "ta betalt nu" (Swish at the
table → mark paid → gate opens, one screen, no admin round-trip) or the
1.6-style audited override ("släpp in, lös betalning senare" →
confirmed-with-balance per 8.2's orthogonality). This also finally
gives the roadmap's deferred "pending indicator on the family list" a
concrete shape: pending families render with the amount owed.

### 9.4 Staff edit event config mid-sale

**Scenario.** Week 3 of a 6-week window: staff raise a price, retire a
T-shirt size, rename an extra, try to delete a ticket type that has 40
sold tickets.

**Recommendation.** P2 makes price/name edits safe by construction —
snapshots don't re-derive; say so in admin help text so staff aren't
afraid to fix typos. Deletion is the sharp edge: `on_delete=PROTECT`
for `TicketType`, `Extra`, and `ExtraChoice` wherever sold rows
reference them, with soft-retire (`is_active=False` — hides from the
form, preserves history) as the offered alternative. `ExtraChoice` as a
real model (1.5) is what makes this enforceable — the JSON-list design
would let staff edit `"XL"` to `"XXL"` and silently orphan every sold
`choice_value` string, the referential-integrity cousin of the import
pipeline's key-matching bug.

### 9.5 Registration window and pre-publish preview

**Scenario.** Staff build the event config Tuesday; registration should
open Sunday at 12:00 after the service announcement. Today literally
nothing gates the public endpoint — a URL-guesser can register the
moment the Event row exists. And staff want to walk through the real
form before it goes live.

**Recommendation.** Punch-list item, arguably the most glaring gap in
the whole Phase 3-6 sketch: `Event.registration_opens_at` /
`registration_closes_at` (nullable datetimes; both null = not
self-serve-registerable at all, which becomes the correct default for
existing/imported events). Outside the window the public page shows the
event info with "öppnar söndag 12:00" — build anticipation, not a 404.
Preview: a staff-generated preview token opens the live form
pre-window with submissions marked `source=staff` and auto-flagged as
test (or simpler and better: preview mode walks the whole form but
disables the final submit — no test-data cleanup problem at all; take
this option).

## 10. Accessibility & edge users

### 10.1 Accessibility needs are first-class, and adults have bodies too

**Scenario.** A child needs a wheelchair-accessible cabin and a quiet
room during worship. A parent has a severe nut allergy and the kitchen
never hears about it. Today `allergies`/`notes` exist **only on
`Child`** — the moment a leaders' conference (parents-only, already
supported by the submit serializer) uses extras with catering, adult
dietary/health capture has nowhere to live. And "shoehorn it into an
Extra" is exactly what 3.2 forbids.

**Why tricky.** Accessibility text is health data (Art. 9) with a
*different audience* than allergies: allergies go to the kitchen and
first-aiders; accessibility needs go to venue planners and leaders.
Merging them into one field means either over-exposing (kitchen reads
about a child's autism) or under-exposing. Camp tools (CampMinder)
model these as separate health-form sections for exactly this reason;
generic tools (Eventbrite) dump both into custom questions and leak
them into every export.

**Recommendation.** Punch-list item: move/add health-shaped capture at
the `Attendee` level — `dietary_health_notes` and `accessibility_notes`
(two fields, two audiences), each under the **same consent machinery**
as `Child.allergies` (for adults, self-attested via their verified
contact or self-scope link — an adult consents to their own data; for
children, guardian-attested as today). Migration path: `Child.allergies`
stays as-is short-term (too much machinery attached to move casually —
the save() backstop, scrub, DSAR); adult fields are additive on
`Parent` first, with base-`Attendee` unification as a separate
deliberate migration later. Staff views segment by audience: kitchen
report gets dietary, logistics gets accessibility, neither gets the
other.

### 10.2 The assistant / ledsagare

**Scenario.** A child's personal assistant attends the whole camp,
sleeps there, eats there — free, per near-universal Swedish practice.

**Recommendation.** No new mechanism: a hidden 0 kr `TicketType`
("Ledsagare/assistent", `is_hidden=True`, unlocked by a code the staff
hand out per 5.4) — or simply staff adding them via 8.6's staff channel
after the family registers and mentions it in a phone call. Document
the pattern for staff; don't build an "assistant" concept.

### 10.3 Skyddade personuppgifter (protected identity)

**Scenario.** A guardian with skyddad folkbokföring (protected
registration — domestic-violence protection, a real and present
population in church family work) must register without their data
leaking into participant lists, kitchen printouts, or group emails.

**Why tricky.** The threat model inverts: the danger isn't the database,
it's the *printed list on the camp notice board*. No mainstream
registration platform handles this; in Sweden it's handled by phone
calls and staff discretion, which actually works — the failure mode is
a *system* that helpfully prints every name everywhere.

**Recommendation.** Don't build a protected-identity workflow into the
public form (advertising the flag is itself a leak). Do two things:
(1) the public event page footer carries the standard line "har du
skyddade personuppgifter? Kontakta oss per telefon i stället" — the
staff channel (8.6) with minimal data entry is the flow; (2) add
`Family.exclude_from_rosters = BooleanField(default=False)`
(staff-settable only) that every list/export/print path must respect —
small field, but it must land *before* the first roster-printing
feature, not after.

### 10.4 The guardian without email

**Scenario.** A grandmother raising grandchildren, no email address,
phone only. The entire lifecycle is email-keyed.

**Recommendation.** Not a public-form problem — solving no-email
self-serve means SMS infrastructure (a new sub-processor, sender-ID
rules, cost) for a tail case. The staff channel (8.6, with its
blankable contact email) *is* the path: she phones the church office,
staff register her in three minutes with witnessed consent. The public
form's footer says so. Revisit SMS only if pilots show real volume.

### 10.5 Cognitive load, screen readers, and the legally-optional-but-do-it-anyway bar

**Scenario.** Guardians include people with dyslexia (common,
underserved by wall-of-text forms), screen-reader users, and the merely
exhausted. DOS-lagen (Swedish web-accessibility law) binds the public
sector, not congregations — irrelevant; the standard is the product's
to set.

**Recommendation.** WCAG 2.1 AA as the working bar for the public flow
specifically: every input labeled (no placeholder-as-label — the
classic sin), error summary linked to fields at the top on failed
validation, visible focus states, form fully keyboard-navigable, step
progress announced to assistive tech, and language plain enough that
the sv text reads at roughly Lättläst level ("Vem följer med?" not
"Ange medföljande deltagares personuppgifter"). This costs near-zero
when built in and a rewrite when bolted on.

---

# Part 2 — The ideal UX flow

**The maxim: as smooth as it can possibly be.** The reference user is a
guardian on a phone, arriving from a link in the congregation's Facebook
group, with a toddler in the other hand, on the bus, on church-basement
wifi. Every design decision below is auditioned against her. Secondary
but binding constraints: no account creation ever, big touch targets,
minimal typing, survives a killed in-app browser, price honesty from the
first screen.

The flow is one mobile-first SvelteKit route, one column, a persistent
progress header ("2 av 5") and a persistent sticky footer (running total
+ primary action button). Every step autosaves to localStorage (8.5);
back always works and never loses data. Target: under 10 minutes cold,
under 5 for a returning family.

### Step 0 — Landing page (the link she tapped)

Public event page: name, dates, place, a photo, price *ranges* per
ticket type ("Barn 400 kr · Ungdom 700 kr · Vuxen 1 100 kr"), what's
included in each (2-3 bullet lines per type — attacking Eventbrite's
"what does this ticket even include" failure), the cancellation policy
line (5.5), coarse availability (1.3), sv/EN toggle (7.4), and one
oversized button: **"Anmäl er"**. Outside the registration window: the
same page with "Anmälan öppnar söndag 12:00" (9.5). Full: the same page
with the waitlist join (1.4). No login wall, no cookie wall, renders
fine inside the Facebook in-app browser (no popups, no third-party
anything).

### Step 1 — "Vem är du?" (contact, and the returning-family fork)

One field: email. On continue, the fork of 4.1: unknown email → straight
into step 2; known email → "Vi känner igen adressen — vi har mejlat en
länk så ni slipper fylla i allt igen" with a parallel "fortsätt utan
länk" escape (never trap someone whose inbox is unreachable right now).
The magic-link path re-enters at step 2 with the roster prefilled.

Email-first is a deliberate ordering: it powers prefill, and it means
the one credential the whole lifecycle hangs on is captured before any
effort is invested (with the typo defenses of 7.3 applied right here —
type-back confirmation and the gmail/gamil hint). Nothing else is asked
on this screen. Notably *not* asked: her name (she'll appear as an
attendee if she's coming, and the form shouldn't presume she is — a
leaders'-conference registrant registering only herself and a
grandmother registering only grandkids are both normal).

### Step 2 — "Vilka följer med?" (the roster/basket)

The roster pattern, not one-person-per-page-forever: a list of person
cards plus two buttons — **"+ Lägg till barn"** and **"+ Lägg till
vuxen"**. Explicitly typed at the moment of adding (P1 — the
adult-inferred-from-email import bug is unrepresentable here).

Tapping either opens a per-person sheet asking only identity-tier
fields: first name, last name (pre-filled with the previous person's
surname after the first — families share surnames, save the typing),
birthdate for children (native date input, numeric keyboard). The sheet
closes back to the roster; the card shows name, auto-assigned ticket
type + price ("Ebba · Barn 0-12 · 400 kr" — 2.2's birthdate windows
doing the assignment invisibly). Where multiple ticket types match
(e.g. hidden-code volunteer vs. standard adult, or day-bundle vs. full),
the card grows a segmented selector — but for the common case *ticket
choice is not a step at all*, it's a consequence of birthdate. This is
the single biggest smoothness win over every generic platform: Planning
Center and Eventbrite both make ticket-type selection the first,
hardest screen ("how many Adult? how many Youth 13-17? what's my kid?");
here nobody ever maps their own child onto a price table.

Multi-day events (2.6): each card gets a "hela lägret / vissa dagar"
segmented control; "vissa dagar" expands day chips (Fre/Lör/Sön) that
map to session bundles. Chips, not dropdowns — thumb-sized, state
visible.

Prefilled roster (returning family): cards arrive pre-created with a
checkmark toggle ("kommer i år?") — deselect the kid who's not coming,
add the baby born since. Hugo's card shows the 4.2 age-out prompt.

The sticky footer total updates with every card. From this moment the
price is always on screen — the anti-Eventbrite commitment: **the total
at the end will be the total she's been watching the whole time.**

### Step 3 — Extras, contextually, per person

The catalog's hardest UX lesson (3.1, 3.2): extras must not be one
undifferentiated checkbox wall at the end (RegFox's signature failure —
40 checkboxes, half irrelevant to your ticket). Placement rules:

- **Per-attendee extras** appear *inside each person's card flow*,
  filtered hard: by `applies_to` (child extras never shown on adult
  cards), by session coverage (Saturday dinner never shown to
  Sunday-only attendees — 3.1's validity rule enforced by construction
  in the UI before the service layer ever sees it). Required-choice
  extras (accommodation) render as radio chips; optional toggles as
  switches; T-shirt as size chips with sold-out states inline
  ("XL slutsåld", disabled, visible — 1.5).
- **Session-scoped extras on multi-day events** render grouped under a
  day heading within the person's card ("Lördag: Festmiddag 150 kr ·
  vegetarisk/vegansk/glutenfri") so the day-association is visual
  structure, not naming convention.
- **Per-registration extras** (cabin, parking with quantity stepper —
  3.3) appear once, as a short separate screen after the roster — never
  repeated per person.

For a simple event (no extras configured) this step doesn't exist —
steps are generated from config, and the smoothest screen is the one
that never renders.

### Step 4 — Health & consent, one person at a time, skip-first

One screen per child (and per adult if the event has catering — 10.1),
but designed skip-first: the primary, largest option is **"Inget att
ange"** — no allergies, no needs. The guardian with three
allergy-free kids taps through this step in three taps. Choosing "Ja,
det finns saker ni behöver veta" expands the dietary/health and
accessibility fields *together with* the consent block — the shared
`ConsentCapture.svelte`, full notice text behind a summary + expandable
detail, explicit unticked checkbox, notice version recorded. The photo
consent toggle (6.3) sits on the same screen, visually separate,
independently optional.

Returning family: this is the "Vi har hälsoinformation om Ebba sedan
tidigare — stämmer den?" screen (4.1/6.1) — read-only display,
[Stämmer] [Uppdatera] [Ta bort], with a fresh attestation recorded
either way. Renewal disguised as review.

This step is deliberately *after* extras and *before* review: late
enough that abandonment before it means no health data was ever typed
(pairing with 1.3's availability re-check, which fires on entry to step
5 — the sold-out race is caught before consent effort, not after), and
early enough that review is genuinely last.

### Step 5 — Review & confirm

One screen: per-person cards (name, ticket, extras, prices), the
per-registration extras, discount line if any, total — matching the
footer she's watched all along. The promo-code field lives here,
collapsed behind "Har du en rabattkod?" (codes are the exception;
don't tax everyone with an empty field — and code-holders know to look;
entering a 5.4 unlock code re-offers the hidden ticket types inline
with a card-level prompt). Cancellation policy restated in one line.
Tapping any card jumps back to that step with everything intact.

Then the legal-footing row: privacy-notice link, the 6.4 registrant
attestation ("Jag är över 18 år och vårdnadshavare/ledare…"), the
honeypot field (invisible), and the submit button with the final
plain-language promise: **"Skicka anmälan — ni betalar inget ännu"**
(paid events) — naming the next step before it happens.

Submission carries the idempotency key (4.4); materialization,
capacity locking (1.2), and promo consumption (5.4) all happen in this
one transaction.

### Step 6 — "Kolla mejlen"

Post-submit screen: the email echoed back in large type, "fel adress?"
inline correction, resend with cooldown (7.3). Honest about the
deadline: "Bekräfta inom 48 timmar." The localStorage draft is cleared
only now — a failed submit keeps everything.

### Step 7 — Verification click → the fork

Free event / zero total (2.5): straight to the confirmation page.
Paid: the payment page — **the flow's second-most-important screen**,
because it's where manual rails either work or generate three weeks of
reconciliation email (5.3). It shows: amount, deadline (7 days, dated,
not relative), and a **Swish QR pre-filled with the congregation's
Swish number, the exact amount, and the reference code as the
message** (generated via Swish's prefilled-QR service, which works with
a Swish Företag number — no merchant API integration needed), plus a
`swish://` deeplink button for the on-phone case ("Öppna Swish").
Bankgiro details beneath, reference code again, copy buttons on every
value. The pre-filled message is the payload: it converts "läger Ebba
o Hugo" bank statements into machine-matchable references at the
source. Below: "Vad händer nu" — verified ✓ → betala (ni är här) →
bekräftelse när betalningen registrerats (vi kollar manuellt, det kan
ta någon dag)". Honesty about the manual step prevents the "I paid,
why no instant confirmation?!" support mail.

### Step 8 — Confirmation

On staff marking paid (or immediately, free events): the confirmation
email (7.1 contents) and its twin page behind the full-scope link:
everything in the booking including the health data the email must
never carry, edit entry points (Part 8 matrix), .ics, practical info.
Self-scope links go out to the other adults (7.2). The page ends with
the timeline: what mail to expect when, who to contact, how to change
or cancel. Nobody should ever wonder what happens next — the flow's
closing promise and the inverse of the classic dead-end "Order
complete." page.

### Mobile-first constraints, named

- **Touch**: every target ≥44px; chips and segmented controls over
  dropdowns everywhere options ≤5; steppers over number inputs.
- **Typing**: the only free-typing in the happy path is email + names +
  birthdates. Everything else is taps. Surname inheritance, birthdate →
  ticket inference, and prefill exist to delete keystrokes.
- **Flaky connection**: the form is client-driven; the network is
  touched at exactly three points (availability check, magic-link
  request, submit). Submit retries safely on the idempotency key.
  localStorage carries everything across a tunnel or a killed webview.
- **Facebook in-app browser**: no popups, no OAuth redirects, no
  third-party cookies, no downloads mid-flow — the .ics arrives by
  email where a real browser handles it.
- **One-handed**: primary actions in the thumb zone (sticky footer);
  progress and total visible without scrolling.

### Known bad patterns, and the specific countermeasure

| Anti-pattern (seen at) | Countermeasure here |
|---|---|
| Fees/total revealed only at final checkout (Eventbrite's signature move) | Sticky running total from the first person card; review total always equals watched total; no service fees exist at all |
| Forced account creation (Cvent, UltraCamp, Realm) | None, ever — magic links carry the whole lifecycle (roadmap's standing decision) |
| Back loses your data (FestivalPro, most RegFox builds) | localStorage autosave per step; back is a first-class navigation; failed submit preserves everything |
| Unclear what a ticket includes (Eventbrite, TicketTailor) | Inclusion bullets on the landing page per ticket type; extras visibly separate |
| Ticket-type matrix as the first screen ("how many Youth 13-17?") — Planning Center, Eventbrite | People first; ticket types inferred from birthdate; the guardian never maps children onto a price table |
| Checkbox-wall of extras irrelevant to your ticket (RegFox, FestivalPro) | Extras filtered per person by applies_to and session coverage, rendered inside the person's context |
| Health data in free-text custom questions leaking into every export (Eventbrite, RegFox, FestivalPro) | Free-text extras structurally impossible (3.2); health capture only in consent-gated dedicated fields |
| Dead-end confirmation, no next steps (nearly everyone) | Every terminal screen and email states what happens next, by when, and the fallback |
| Sold-out discovered after full form entry (TicketTailor) | Coarse availability on landing, re-check before consent step, typed-work carryover into waitlist join |
| Payment reference chaos on manual rails (every church's current spreadsheet) | Pre-filled Swish QR with amount + reference code; deadline dated; manual-step honesty |

---

# Part 3 — Implications for the Phase 3-6 model (punch list)

Concrete deltas this exercise surfaced against the Phase 3-6 sketch in
`event_registration_and_mailing.md`, in rough order of leverage. Items
marked **(P3)** etc. indicate which phase they amend; **(new)** means no
phase currently owns them.

1. **(P3) `Extra.session` FK (nullable) + `Extra.applies_to`** — the
   commissioned session-scoped-extras fix (3.1); validity rule "extra
   requires session coverage" in the service layer; edit flow confirms
   (never silently drops) orphaned extras.
2. **(P3) Promote `Extra.choices` JSON → `ExtraChoice` model** with
   `price_delta`, per-choice `stock`, `is_active` soft-retire;
   `RegistrationExtra.choice_value` string → FK (1.5, 9.4). The JSON
   list re-creates the import pipeline's ambiguous-string-matching bug
   inside our own schema — kill it before first migration, not after.
3. **(P3) No free-text extras — structurally.** `Extra` supports
   toggle/choice/quantity only; add `Extra.required`,
   `Extra.default_selected`, `RegistrationExtra.quantity` + unique
   `(registration, extra, attendee)` (3.2, 3.3, 2.1).
4. **(P3) `TicketType` gains `min_birthdate`/`max_birthdate`** (auto
   ticket-type assignment; subsumes åldersspann and årskurs cohorts —
   2.2), **`available_from`/`available_until`** (early-bird window,
   currently prose-only — 2.3), **`is_hidden`** (5.4), **`kind` +
   `sessions` M2M** for day bundles (2.6), and nullable **`capacity`**.
5. **(new) Capacity**: nullable `capacity` on `Event` and `Session`;
   one accounting rule (all non-cancelled registrations hold seats);
   `select_for_update` discipline in the submission transaction; no
   separate hold system (1.1, 1.2). Staff-only audited override (1.6).
6. **(new) `WaitlistEntry`** — thin, no child data, no health data;
   offer tokens with 48h expiry; fits-first offer policy; hard-delete
   at event end (1.4). Sold-out submit converts typed work into a
   waitlist join (1.3).
7. **(new) `PaymentEvent` append-only ledger** + `partially_paid`
   status; `Payment.amount` becomes owed-side; balance derived.
   Carries partial refunds, under/overpayment, and edit deltas —
   status and balance become orthogonal, confirmed never regresses to
   pending_payment over an edit (5.1, 5.3, 8.2).
8. **(P3) Paid-ness = `calculate_total(registration) > 0`**, not
   `Event.is_paid`; zero-total registrations confirm directly (2.5).
9. **(P5) `PromoCode` gains `applies_to_ticket_types` M2M and
   `unlocks_ticket_types` M2M**; `Registration.promo_code` FK +
   `discount_amount` snapshot; one code per registration enforced by
   shape; usage counted at submission under lock, released by TTL
   sweep (5.4).
10. **(P6, upgraded priority) Bulk/group-leader flow = RegistrationGroup**
    with one minimal Family+Registration per child; leader =
    registrant/payer, guardian = consent-holder, completing health data
    via guardian-scoped token post-hoc; the bulk flow contains zero
    health fields (4.3). This makes Phase 6 load-bearing rather than
    "rarest case, build last" — re-rank it.
11. **(P4) Session/day coverage, capacity, and consent rigor apply to
    edits**: same capacity service, same `ConsentCapture`, contact-email
    change re-verifies, new-adult self-links sent on add; scope matrix
    per 8.1 including self-removal; type-to-confirm on full cancel
    (8.3, 8.4).
12. **(new) `Registration.source`** (`self_serve`/`staff`/`import`) +
    blankable contact email for staff source; walk-up registration
    drives the same services with staff-witnessed consent and immediate
    payment marking (8.6); check-in screen gets "ta betalt nu" (9.3).
13. **(new) `Event.registration_opens_at`/`registration_closes_at`** +
    submit-disabled preview mode — nothing currently gates the public
    endpoint at all (9.5).
14. **(new) `Event.refund_cutoff` + `cancellation_policy_text`** —
    advisory enforcement, shown pre-payment and in confirmation (5.5).
15. **(new) `Registration.locale`** snapshot driving all lifecycle
    email/pages; no content translation tables (7.4).
16. **(new) Attendee-level `dietary_health_notes` +
    `accessibility_notes`** (two fields, two audiences) under the
    existing consent machinery — adults currently have no health capture
    at all, which breaks the first catered leaders' conference (10.1).
17. **(new) `ConsentRecord` generalization pulled forward with `photo`
    type** — the registration form is the capture moment Swedish
    congregations currently miss entirely (6.3);
    `health_consent_registration` FK for guardian-attestation identity
    (6.2); event-aware renewal sweep at T−30 checking validity through
    `event.end_date` (6.1).
18. **(new) `Registration.idempotency_key`** (unique, client-minted) +
    post-verification soft-dedup sweep on (event, normalized child
    name, birthdate) → `pending_review`; never auto-merge (4.4).
    `merge_families()` audited service before any merge UI (9.1).
19. **(P4) Returning-family prefill** via email-recognition magic link;
    reuse existing Family/Attendee rows (`created_new_family=False`
    semantics already fit); health data shown read-only post-link as
    review-and-reattest, never injected into form fields (4.1).
    `promote_child_to_parent()` audited service for aged-out children
    (4.2).
20. **(decision recorded, no build) No server-side drafts** —
    localStorage autosave only; cross-device resume out of scope; if
    ever needed, the compliant shape is submit-early-edit-later via
    Phase 4, not a draft store (8.5).
21. **(new) Soft-delete for edit-removed tickets/extras**
    (`removed_at`) so receipts and refund math keep history; TTL sweep
    hard-delete for unverified registrations unchanged (5.2).
22. **(new) Email-context whitelisting** — templates render from a
    dedicated safe-fields dataclass, upgrading "no health data in
    email" from convention to structure (7.1); day-5 payment reminder
    and T−7 practical-info mail added to the transactional sequence
    (7.2); pre-verification contact-email correction (7.3).
23. **(new, small but time-sensitive) `Family.exclude_from_rosters`**
    for skyddade personuppgifter — must exist before the first
    roster-print feature ships, and the public page points protected
    persons at the staff channel (10.3).

Items 1-4 amend Phase 3 before it's built — cheap now, migrations
later. Items 5-7 and 13 are the pre-pilot floor: a real event without
capacity, a registration window, and honest money accounting isn't
pilotable. Item 10 re-ranks Phase 6. The rest sequence naturally behind
Phase 4.

---

# Part 4 — What this catalog deliberately does not support, and what it silently omits

Companion audit to Parts 1-3: a consolidated pass over every "don't
build" call already scattered through the case catalog, plus a search
for cases the catalog never raises at all. The first list is decisions
that were made; the second is blind spots that still need one.

## Explicitly excluded (a decision was made)

| Case | Why excluded | Assessment |
|---|---|---|
| Seat holds while the form is open (1.3) | Avoids hold/expiry machinery for a phone-glance page view | Right call — sold-out→waitlist carryover covers the actual pain cheaper |
| `Extra` gated by ticket type, `Extra.ticket_types` M2M (3.4) | Session-scope + `applies_to` cover most real cases; deferred as a small additive migration otherwise | Right call, but watch for the lodging-on-day-pass edge actually surfacing in a pilot |
| Split payment between two households (4.5) | Swedish norm is "one pays, other Swishes them back" — off-system | Right call, matches the manual-rail reality; a split ledger would be pure reconciliation cost for zero real need |
| Legal custody modeling (4.6) | "Don't model custody"; consent text states what's being attested instead | Right call — modeling vårdnadshavare relationships correctly is its own project; the honest-attestation-text fallback is the right weight |
| Personnummer collection (4.7) | Permanent refusal, framed as a selling point | Right call, worth keeping — every identifier added widens breach/export blast radius for zero function gain |
| Automated tiered refund-percentage enforcement (5.5) | "The pastor refunds anyway" — a rules engine would be authoritative-looking fiction | Right call — correctly reads the actual social process over the stated policy |
| Operator-tunable payment TTL (5.6) | Fixed at 7 days; tunability framed as a support foot-gun | Worth pressure-testing: a 3-day retreat with capacity 12 may genuinely need a shorter TTL. A per-event override is a smaller ask than per-operator tunability and isn't ruled out by the same reasoning |
| Under-18 self-registration (6.4) | V1 hard rule: registrant must be 18+ or a leader | Right call for now; already flagged as a future per-congregation policy relaxation, not closed forever |
| Server-side drafts / cross-device resume (8.5) | localStorage-only; a draft store would hold Art. 9 data outside consent/export/erasure machinery | Right call — the reasoning (drafts either become non-compliant shadow storage or duplicate all of materialization) holds |
| Event transfer to a different date (8.7) | Cancel + single-use 100% promo code for the new event does the same job | Right call — no new model surface for a rare case |
| First-class "assistant/ledsagare" concept (10.2) | Hidden 0 kr ticket type instead | Right call, right-sized |
| Protected-identity (skyddade personuppgifter) workflow in the public form (10.3) | Advertising the flag in a public form would itself be a leak; phone-based staff channel instead | Right call — a system *feature* here would be worse than the current staff-discretion status quo |
| SMS / no-email self-serve (10.4) | New sub-processor, sender-ID rules, cost, for a tail case; staff channel absorbs it | Right call for v1, but this is the population (grandmothers raising grandchildren) churches most want not to fail — track pilot volume closely, as the doc already says |
| Translation of event content (7.4) | No translation tables; congregations write bilingual text manually | Right call, matches Eventbrite's approach |
| VAT/tax line modeling (2.7) | Swedish ideella föreningar aren't moms-registered for member activities | Right call for the actual customer base |
| Payment execution / online gateway (implicit throughout, e.g. 5.1, 5.3) | System only *records* Swish/Bankgiro reconciliation, never moves money | Inherited from the existing `Payment` model, not a decision this doc made — but it means every payment case assumes a Swedish bank account on the payer's side (see below) |

## Never addressed (no decision was made)

Not "decided against" — these simply never appear across 60+ cases.
Whether they warrant a case entry depends on how far the target market
stretches beyond a single Swedish congregation's camp/conference:

1. **Ticket transfer to a different attendee.** "My kid can't come, my
   neighbor's kid takes the spot" is distinct from cancel+waitlist —
   no case discusses reassigning a paid ticket to a new name. Given
   4.5's own reasoning about Swish-between-friends being normal social
   practice, this will come up. Likely a documented non-feature
   ("cancel yours, they register fresh, sort out money between
   yourselves") rather than a build — but it should be a stated
   decision, not silence.
2. **Foreign/non-Swedish-bank payers.** 7.4 raises bilingual
   congregations explicitly but never connects that to *payment
   feasibility* — Swish and Bankgiro both assume a Swedish bank. An
   international guest family cannot pay through either rail. Worth at
   least a documented staff-workaround (cash/international transfer
   handled off-system, recorded as a `PaymentEvent`), the way 10.4
   handles no-email guardians.
3. **Invoice/faktura payment for institutional payers.** Municipal
   youth grants (kommunbidrag) or a school sponsoring a class trip
   often *require* an invoice, not a QR code. Possibly genuinely out
   of scope for a "guardian on a bus" product, but if any pilot
   congregation serves confirmation classes with municipal funding,
   this surfaces as a blocking gap, not a nice-to-have.
4. **Recurring/term-based registration.** Every case assumes one
   bounded `Event` (a camp, a conference). Weekly children's-club
   terms or a multi-month confirmation program aren't modeled at all —
   sign-up-once-for-a-term is a different shape than sign-up-per-camp.
   Possibly correctly out of scope if "event registration" is
   deliberately camp/conference-only; worth confirming that's the
   intended boundary rather than an oversight.
5. **Bundle/loyalty pricing across separate Events.** "10% off if you
   also register for the youth weekend" or a returning-camper discount
   — 5.4's promo codes can approximate this manually (issue a code),
   but there's no modeled relationship between two `Event` rows.
   Likely fine to leave as a promo-code workaround; flagging so it's a
   conscious call rather than an omission.
6. **Guardian-initiated data export/erasure from the confirmation
   page itself.** 6.5 covers DSAR as a backend/staff-mediated export
   scope, but the UX flow (Part 2) never gives the guardian a
   self-service "see everything we hold" or "delete us" action from
   the full-scope link — everything currently routes through staff.
   Given the product's GDPR-forward positioning, this is worth at
   least a one-line decision (self-service vs. staff-mediated
   erasure), the same treatment 10.2/10.4 already give their cases.

Items 1, 2, and 6 are the ones most likely to generate real support
email in year one — worth at least a documented "we thought about
this, here's the workaround" line. Items 3-5 are more plausibly
genuine non-goals given the product's camp/conference framing, but are
listed so that's a decision on record rather than an accident.

