# Self-Serve Event Registration & Mailing

## Status (2026-07-09)

**Phase 5 (promo codes) shipped** — see the case catalog's §5.4 for the
full design and its own status note. `Event.price`/flat-fallback events
can carry a code too (a whole-total discount applies fine there), but the
hidden-ticket-type unlock case only matters for itemized events with a
`TicketType.is_hidden=True` row to unlock.

## Status (2026-07-08)

**Update 2026-07-08**: Phase 2 (Swish/Bankgiro payment) also shipped, on the
same branch, commit `116040c` — see [[tryggare-payment-verification-status]]
in memory. PR #18 open, not yet merged. `PENDING_PAYMENT` is no longer dead
code; a paid event correctly blocks auto-confirm.

Phases 3-6 below are a priorities/data-model planning pass done the same day,
in response to real customer complexity (food/no-food, promo codes,
age-tiered ticket pricing similar to the FestivalPro import's prefix
mapping, longer-retention consent, and group bookings that don't fit neatly
inside one `Family`). Nothing in Phases 3-6 is built yet — this is design,
not status.

## Status (2026-07-07)

Phase 0 (transactional email, `notifications` app) and Phase 1 (free-event
self-serve registration, `registrations` app) are implemented on
`feature/self-serve-registration` (branched from `feature/transactional-email`).
The open design questions below are resolved for phase 1 — kept here for the
reasoning, not as still-open decisions:

- **Registration state before payment**: resolved as a thin `Registration`
  grouping model (event FK, status, reference code, contact email, hashed
  verification token) owning N tickets — not a field on `EventTicket`/
  `SessionTicket`. State machine: `pending_verification` → (email verify) →
  `confirmed` (free) / `pending_payment` (paid, phase 2) / `pending_review`
  (verified email exactly matches an existing guardian on a *different*
  family — routed to a staff queue rather than auto-attached). A ticket only
  counts toward check-in eligibility once its `registration.status ==
  confirmed` (`checkins/eligibility.py::registration_checkin_gate_error`).
- **Guardian portal reversal / abuse protection**: resolved as email
  verification (hashed one-time token) as the primary control, not CAPTCHA —
  dedup + resend-cooldown on `(event, contact_email)` is the actual abuse
  multiplier control; per-IP throttle stays deliberately loose (bulk on-site
  registration from one venue wifi hotspot is a real workload, per the
  FestivalPro/Planning Center import precedent) plus a honeypot field. No
  persistent guardian account/login introduced — same one-time-link shape
  already used for `/qr/[token]`.
- **Consent capture without a staff intermediary**: resolved by extracting
  the staff `AddFamilyPanel.svelte` consent block into a shared
  `ConsentCapture.svelte`, and `FamilyCreateSerializer.create()`'s logic into
  `families/services.py::create_family_with_members()`, so both paths get
  identical validation/notice-versioning rigor.
- **Email content minimization**: `notifications/providers.py` never
  receives allergy/health text — enforced by convention (registration emails
  only ever mention event name + reference code), not by code-level
  filtering.

Still open / explicitly deferred from phase 1: CAPTCHA (revisit only if real
abuse is observed), a bespoke staff review UI for the `pending_review` queue
(Django admin is enough for now), fuzzy family-dedup beyond exact-email-match,
capacity limits, and a UI treatment for unconfirmed registrations on the
staff check-in screen beyond "check-in is blocked with an error" (the backend
gate is enforced; the visual "pending" indicator on the family list is not
yet built — see `checkins/eligibility.py`'s docstring). Marketing mailouts
(the other half of this doc) are entirely unbuilt — everything below this
point still describes future work.

## Goal

Extend Tryggare Moln beyond on-location check-in to cover the full event
lifecycle: guardians register themselves and their children for an event
online (instead of staff entering everyone, or importing from FestivalPro /
Planning Center), consent gets renewed automatically as it approaches
expiry, and the congregation can send confirmations, receipts, and
(separately) newsletters.

## Why now

- `Family` / `Parent` / `Child` (MTI on `Attendee`) plus `EventTicket` /
  `SessionTicket` already represent everything a registration needs to
  produce — today it's just populated by staff or import.
- `Child.health_consent_status` and the staff-attested consent UX already
  exist; registration would reuse the same field, just captured directly
  from the guardian instead of relayed by staff.
- Consent renewal (18-month validity window, then an automated
  extension-request email) is already a scoped idea, blocked only on email
  infrastructure existing at all.

## Two legally distinct kinds of email — do not merge them

1. **Transactional** (registration confirmation, payment receipt,
   consent-renewal/withdrawal link): legitimate interest / contract
   necessity. No separate opt-in required. Build this first — it's what's
   already blocking the consent-renewal feature.
2. **Marketing mailouts** (newsletters, "save the date"): under Swedish
   marknadsföringslagen this needs prior opt-in consent, or the "existing
   customer, similar service, opt-out offered" soft-opt-in exception —
   murky for a nonprofit church context. Safer path: an explicit,
   unticked-by-default `marketing_opt_in` per parent (not per family — it's
   an individual's inbox and right to object), enforced at send time, with
   an unsubscribe link and suppression list on every send. Don't reuse the
   health-consent machinery for this.

## Design considerations (open, not yet decided)

- **Guardian portal reversal.** The consent-capture design deliberately
  avoided a guardian portal ("guardians never log in, staff enter
  everything"). A public registration form *is* a guardian portal for that
  one step — needs its own abuse-protection story (CAPTCHA, rate limiting,
  email verification of the registering parent), since it's a public
  endpoint that *writes*, unlike the existing public `/qr/[token]` endpoint
  which is read-only and privacy-minimizing by design.
- **Registration state before payment.** A submitted registration shouldn't
  be check-in-valid until staff (or later, an automated payment check)
  confirms payment — see `payment_processing.md`. Whether that's a
  `pending` state directly on `EventTicket`/`SessionTicket`, or a thin
  grouping `Registration` model that owns N tickets plus one payment
  record, is worth deciding deliberately.
- **Consent capture without a staff intermediary.** Arguably a stronger
  legal position (Art. 9(2)(a) directly from the data subject) but the UX
  must carry the same explicit-consent rigor and notice-versioning as the
  staff-facing flow.
- **Email content minimization.** Never put allergy/health text in an
  email body — it lives in the guardian's inbox and the SMTP provider's
  logs indefinitely, outside the app's own retention/anonymization
  pipeline.
- **Sending domain separation.** Use separate sending (sub)domains for
  transactional vs. marketing mail, so a bulk-send deliverability problem
  never threatens confirmation/consent-renewal mail.

## SMTP provider — sub-processor implications

Whichever SMTP relay is used becomes a new GDPR sub-processor once it
carries guardian email addresses and message content — same treatment
GleSYS already got for hosting:

- Confirm the provider offers a PUB-avtal / databehandlaravtal for the
  SMTP/email product specifically, not just assumed from general hosting
  terms.
- Add them to the sub-processor list in `docs/legal/TRYGGARE_MOLN_DPA.md`
  and `TECHNICAL_ANNEX.md`.
- Confirm mail infrastructure location (EU/Nordic residency) — Tryggare
  Moln's own hosting is self-hosted (mikro, Swetzéns Ekonomitjänst AB's own
  hardware, no third-party cloud provider), so an email sub-processor
  would be the *first* third-party infrastructure provider in the chain,
  not a second one alongside an existing hosting sub-processor.

### Findings for Simply.com (researched 2026-07-07)

Simply.com A/S (Denmark, part of team.blue, formerly UnoEuro) is the
candidate provider. Research findings:

- **DPA exists and explicitly covers email.** Self-service — download/
  e-sign via the Control Panel, no sales contact needed
  ([simply.com/en/compliance](https://www.simply.com/en/compliance/)).
  Annex 1 names "webhotel og e-mail" as covered systems, including email
  backups. No plan-tier gating found. The actual template text was only
  recovered via a third-party mirror of a signed copy (v1.7, 2020-03-26),
  not fetched directly from simply.com — **re-verify the current version
  directly with Simply before citing it in a real DPA/sub-processor list.**
- **Sub-processors:** only 3 disclosed (hardware disposal, backup vendor,
  a website-builder product) — no dedicated email-delivery/ESP
  sub-processor listed. Mail appears to run on Simply's own Danish infra.
- **Data residency:** Denmark, EEA-only processing required by the DPA
  itself (§3) — consistent with the existing Sweden/GleSYS residency
  story, just a different EU country.
- **Operational blocker, bigger than the DPA question:** `smtp.simply.com`
  (the relay usable from an *external* server like the GleSYS-hosted
  Django app) explicitly **prohibits newsletters, bulk mailings, and
  automated marketing email** in its terms, and auto-suspends past ~300
  messages/4h. The unlimited-volume alternative, `websmtp.simply.com`, only
  works for scripts running **on Simply's own web hosting** — not usable
  from GleSYS at all. No SPF/DKIM/DMARC guidance found.

**Implication:** transactional volume (confirmations, receipts,
consent-renewal mail) is almost certainly fine under the ~1800/day cap at
church scale, but Simply's own ToS rules out using it for the *marketing*
mailout track categorically, regardless of consent/opt-in correctness on
Tryggare Moln's side. If marketing mailouts are ever built, they need a
separate provider from transactional mail — which also cleanly reinforces
the "separate sending domains" design point above, since it'd be a fully
separate service, not just a separate subdomain. Open questions still
needing a direct support inquiry: whether the sub-processor list is
complete for mail delivery specifically, and the current live DPA
version/date.

**Explicitly out of scope for now:** a pluggable/multi-provider mail-sending
abstraction (so a future marketing provider could be swapped in without
touching the transactional path) would be the right shape once a second
provider is actually needed — but building that abstraction ahead of having
a second provider would be speculative. Wire the transactional path directly
to Simply for now; revisit pluggability only when a real marketing-mail
provider is chosen.

## Implementation sketch

### Backend

- Django email backend configured against the SMTP relay; a thin
  `notifications` app for transactional sends (confirmation, receipt,
  consent-renewal, withdrawal) kept separate from marketing sends so the
  opt-in check can't be bypassed by accident.
- Public registration endpoint(s): create `Family`/`Parent`/`Child` plus
  pending tickets; reuse `health_consent_status` capture; rate-limited and
  CAPTCHA-gated.
- `marketing_opt_in` boolean + timestamp on `Parent`, enforced at send
  time, with a public, idempotent unsubscribe endpoint.

### Frontend

- Public registration flow (SvelteKit route, unauthenticated) parallel to
  the existing staff `AddFamilyPanel.svelte`, sharing validation logic
  where practical.
- Consent-renewal and withdrawal-link landing pages (public, token-based,
  similar pattern to `/qr/[token]`).

## Phases 3-6: itemized registration, self-service, promo codes, group booking

Grounding check done before designing this: "a parent registers alone for a
leaders' conference, no kids" already works today with zero model changes —
`RegistrationSubmitSerializer.validate()` only requires *either* parents or
children, not both (`registrations/serializers.py`). The real gap is that
self-serve registration currently has **no choices in it at all** — every
attendee gets one flat `EventTicket` at `Event.price`
(`registrations/views.py::_create_registration`). Ticket types, extras, and
promo codes are the first itemization layer, not a tweak to an existing one.

### Phase 3 — Ticket types & extras

```python
class TicketType(models.Model):
    event = FK(Event, related_name="ticket_types")
    name = CharField          # "Adult", "Youth (13-17)", "Child (0-12)"
    price = DecimalField
    applies_to = CharField(choices=["parent", "child", "either"])
    sort_order = IntegerField

# EventTicket / SessionTicket gain:
    ticket_type = FK(TicketType, null=True)     # null = staff/import ticket, unaffected
    price_at_registration = DecimalField        # snapshot — never recompute after the fact

class Extra(models.Model):
    event = FK(Event, related_name="extras")
    name = CharField           # "Lunch Friday", "T-shirt"
    price = DecimalField(default=0)
    per_attendee = BooleanField(default=True)   # vs. per-registration (e.g. a shared cabin)
    requires_choice = BooleanField(default=False)
    choices = JSONField(blank=True, default=list)   # e.g. ["S", "M", "L", "XL"]

class RegistrationExtra(models.Model):
    registration = FK(Registration, related_name="extras")
    extra = FK(Extra)
    attendee = FK("families.Attendee", null=True)   # null if per-registration
    choice_value = CharField(blank=True)
    price_at_registration = DecimalField
```

`registrations/pricing.py::calculate_total(registration)` sums ticket types
+ extras; called at the same lazy `Payment`-creation point
`verify_registration()` already uses for phase 2. "Early bird" pricing
should be a `TicketType` with a validity window, not a promo code — and
sibling/multi-child discounts (common at church camps) are an automatic
rule, not a code — keep both out of Phase 5's `PromoCode` if they come up
later.

**Priority: first.** Everything below depends on itemized pricing existing.

### Phase 4 — Edit + self-service + notify other adults

Reuses the existing token pattern (`Registration.verification_token_hash`,
same shape as `/qr/[token]`) rather than a login system — consistent with
the explicit prior decision above that guardians never get a persistent
account. Two token *scopes* answer both the edit-permission question and
the "who can manage what" question in one mechanism:

```python
class RegistrationAccessToken(models.Model):
    registration = FK(Registration, related_name="access_tokens")
    attendee = FK("families.Attendee", null=True)   # null = full-booking scope
    token_hash = CharField
    scope = CharField(choices=["full", "self"])
    expires_at = DateTimeField
    used_at = DateTimeField(null=True)
```

- **full** scope (no `attendee`): only the original registrant — edit the
  whole booking, add/remove attendees, change ticket types/extras, cancel,
  see payment status.
- **self** scope (`attendee` set): any adult attendee on the registration —
  limited to their own contact info and, if they guardian a child on the
  booking, that child's allergy/health notes.

Sending every adult attendee their own **self**-scoped link at confirmation
*is* the answer to "do we email other adults when they're signed up" — one
mechanism serves both asks, no separate notification system needed.

**Priority: second.** High UX value once real guardians are relying on
this for a real conference (typos, late additions, dietary changes are
routine), and self-contained — doesn't depend on Phase 5 or 6.

### Phase 5 — Promo codes

```python
class PromoCode(models.Model):
    event = FK(Event, related_name="promo_codes")
    code = CharField()                # unique per event
    discount_type = CharField(choices=["percent", "fixed"])
    discount_value = DecimalField
    max_uses = IntegerField(null=True)     # null = unlimited
    uses_count = IntegerField(default=0)
    valid_from = DateTimeField(null=True)
    valid_until = DateTimeField(null=True)
    active = BooleanField(default=True)
```

Applied against the whole `Registration` total from Phase 3's itemized
pricing — this is why itemization has to land first.

**Priority: third.** Small, bolts on; not a launch blocker.

### Phase 6 — Group booking (two families registering together)

The only case here with real schema impact: one checkout/payment spanning
attendees from more than one `Family`. `Registration.family` and `Payment`
(currently `OneToOne` to `Registration`) are both 1:1 today, and that's
*correct* for check-in/pickup purposes — an adult from Family A shouldn't
become part of Family B just because they co-registered for a retreat.
**Decided 2026-07-08**: keep `Family`/`Registration` 1:1, and add the
group concept only at the checkout layer:

```python
class RegistrationGroup(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = DateTimeField(auto_now_add=True)

# Registration gains:
    group = FK(RegistrationGroup, null=True, related_name="registrations")
```

`Payment` moves from `OneToOne(Registration)` to `OneToOne(RegistrationGroup)`
when a registration is grouped; an ungrouped `Registration` keeps owning its
own `Payment` exactly as today (Phase 2 behavior unchanged for the common
case). Each family in the group still gets its own `Registration` row (own
tickets, own family-matching/`pending_review` logic per contact email) — the
group only ties them together for one combined checkout/payment.

**Priority: last.** Rarest case in practice (a joint leaders'-conference
booking, not everyday registration) and the most invasive change to the
Phase 0-2 model. Until built, staff can still handle a joint booking
manually, or one adult can register both families under themselves as a
workaround.

### Cross-cutting: consent generalization

By Phase 6 there will be three consent-shaped fields in play:
`Child.health_consent_status` (exists), `marketing_opt_in` (sketched
above, unbuilt), and "consent to store details longer than default
retention" (raised 2026-07-08, unbuilt). Rather than a third bespoke
boolean, generalize once any of the unbuilt ones gets scheduled:

```python
class ConsentRecord(models.Model):
    subject = FK("families.Attendee")   # or a GenericFK if family-level consent is ever needed
    consent_type = CharField(choices=["health", "marketing", "extended_retention"])
    granted_at = DateTimeField
    expires_at = DateTimeField(null=True)
    notice_version = CharField
```

Same audit shape as the existing health-consent pattern, one place to
reason about expiry sweeps instead of three. Not urgent on its own — do
this when the second or third consent type is actually implemented, not
speculatively ahead of that.

## Dependencies

- SMTP relay + DPA in place before any real email goes out.
- Payment processing (or an explicit "free event" path) before
  registrations can be marked check-in-valid.
- Phase 3 (itemized ticket types/extras) before Phase 5 (promo codes) —
  a discount needs an itemized total to discount.

## Priority

Medium-high. The transactional-email half unblocked an existing
pre-launch legal gap regardless of what else in this doc gets built (done).
Within what's left: Phase 3 (ticket types & extras) first — everything
else depends on it — then Phase 4 (edit/self-service/notify), then Phase 5
(promo codes), then Phase 6 (group booking) last.
