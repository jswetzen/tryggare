# Self-Serve Registration: Data Model Hardening

## Status (2026-07-09): all phases (A-D) implemented

Findings from an architecture review of PR #18 (`feature/self-serve-registration`,
commits `7d69d26`..`3f97aa6`) — the full stack from transactional email through
Swish/Bankgiro payment, ticket types/extras/pricing, registration window, the
`PaymentEvent` ledger, and promo codes. Nothing here is a merge blocker; the
branch is unusually well-tested (see `registrations/tests_*.py`,
`checkins/tests_registration_gate.py`) and most of what's flagged is a gap at
the *edges* of an otherwise coherent state machine, not a structural problem
with it. This doc is the punch list for closing those edges, prioritized by
impact-per-effort. See `event_registration_ux_case_catalog.md` for the design
rationale behind the model itself — this doc doesn't relitigate any of that.

Every item below (A1/A2, B1/B2, C1/C2, D1-D3) is implemented and tested —
304 backend tests pass (2 pre-existing, unrelated `printing.tests.test_ws_auth`
failures reproduce identically on `3f97aa6`, before any of this work). One
deliberate deviation from the literal spec: C1's invariant 2 ("received −
refunded + adjusted ≤ amount") is enforced for `ADJUSTMENT` events only, not
`RECEIVED` — enforcing it universally would have silently broken the
already-shipped, already-tested negative-balance overpayment feature from
`event_registration_ux_case_catalog.md` §5.3
(`test_overpayment_is_paid_with_negative_balance`). Since a `REFUNDED` event
can only ever shrink the checked expression (never violate it, given
invariant 1 already holds), the only event kind invariant 2 can actually
reject is an oversized `ADJUSTMENT` — which is also the reading that keeps
both invariants' stated goals intact. See `registrations/services.py::
record_payment_event`'s docstring for the full reasoning.

Not covered here: anything already flagged as deliberately deferred elsewhere
(`TicketType.capacity` unenforced, no waitlist, no bespoke `pending_review`
staff UI beyond Django admin) — those are known, intentional gaps, not bugs.

## Phase A — independent, cheap, do first (~1 day total) — DONE

### A1. Cap verification-resend volume (email-bombing vector) — DONE

**Problem.** `registrations/views.py::_resend_verification` has a 10-minute
per-registration cooldown but no cap on total resend count, and each resend
resets `Registration.expires_at`. Combined with the (deliberately loose)
`registration_submit` throttle of 30/hour per IP, an attacker can put a
victim's real email in `contact_email` for any open event and trigger up to
~144 unsolicited "confirm your registration" emails/day, indefinitely — the
row never expires because every resend refreshes its own TTL.

**Fix.** Cap total resends per registration (e.g. stop actually resending
after N, while still returning the same 200 so as not to leak the cap to a
prober), or derive the TTL from `submitted_at` instead of resetting from
`verification_sent_at` on every resend so the row has a hard lifetime
regardless of resend count.

**Touches:** `registrations/views.py` (`_resend_verification`), maybe a new
field or a computed cap check. Tests: extend `registrations/tests_dedup.py`.

### A2. Guard against an empty-sessions `session_bundle` TicketType — DONE

**Problem.** Nothing validates that a `TicketType` with `kind=SESSION_BUNDLE`
has at least one row in its `sessions` M2M (`events/models.py` has zero
`clean()` methods anywhere). If staff save one without attaching sessions,
`_materialize_ticket` (`registrations/views.py`) loops over an empty
queryset and creates **zero** `SessionTicket` rows for that attendee — they're
billed nothing for the line and end up with no ticket record for the event at
all, despite completing the full submit→verify flow.

**Fix.** Add validation — either a `clean()` on `TicketType` enforced via the
admin, or (belt-and-suspenders, catches non-admin paths too) a raise in
`_materialize_ticket` if `ticket_type.kind == SESSION_BUNDLE and not
ticket_type.sessions.exists()`.

**Touches:** `events/models.py` and/or `registrations/views.py`. Tests: add to
`registrations/tests_pricing.py` alongside the existing bundle tests.

## Phase B — state-machine completion (~1 day, B1 before B2's last piece) — DONE

### B1. Give `pending_review` a real resolution path — DONE

**Problem.** `verify_registration` routes to `PENDING_REVIEW` when a verified
email matches an existing `Parent` on a different family (the anti-spoofing
dedup gate). Nothing ever transitions it out — no service function, no admin
action. `Registration.status` isn't in `RegistrationAdmin.readonly_fields`,
so the only escape hatch today is a raw field edit in Django admin, which
skips Payment creation for a paid event, the confirmation/payment-instructions
email, and the app's own `log_audit` call — everything every *other*
transition gets via a dedicated service function.

**Fix.** Add `resolve_pending_review(registration, *, action: Literal["confirm",
"reject"], resolved_by)` in `registrations/services.py`, mirroring
`confirm_registration_despite_balance`'s pattern (handle Payment creation +
email if `action="confirm"` and the total is nonzero; on `action="reject"`,
transition to `CANCELLED` and — see B2 — release any promo-code use). Wire as
two `RegistrationAdmin` actions replacing the raw field edit.

**Touches:** `registrations/services.py`, `registrations/admin.py`. Tests:
new `registrations/tests_pending_review.py` or extend `tests.py`.

### B2. Release `PromoCode.uses_count` on expiry/cancellation — DONE

**Problem.** This one is a documented gap, not just an observed one —
`docs/roadmap/event_registration_ux_case_catalog.md` §5.4 specifies usage
accounting as "released by the TTL sweep on expiry/cancellation — identical
semantics to capacity." The shipped code (commit `3f97aa6`) implements the
increment (`_resolve_promo_code`, correctly locked and race-tested) but never
implements the release: `tasks.py`'s two sweeps and `admin.py`'s
`cancel_registrations` never touch `promo_code`/`uses_count`. A `max_uses`-
limited code permanently loses a slot to every abandoned or cancelled
registration that used it.

**Fix.** Add `release_promo_code_use(registration)` to
`registrations/services.py` (an `F('uses_count') - 1` update, floored at 0
defensively), called from:
- `sweep_expired_registrations` (`tasks.py`)
- `sweep_unpaid_registrations` (`tasks.py`)
- `RegistrationAdmin.cancel_registrations` (`admin.py`)
- B1's new `resolve_pending_review(..., action="reject")`

**Touches:** `registrations/services.py`, `registrations/tasks.py`,
`registrations/admin.py`. Tests: extend `registrations/tests_promo_codes.py`
and `registrations/tests_materialization.py` (which already tests the
sweeps) with one case per release point.

## Phase C — payment ledger hardening (~half day) — DONE

### C1. Constrain the `PaymentEvent` ledger so `Payment.status` can't misrepresent settlement — DONE (see deviation noted above)

**Problem.** `Payment.recompute_status()` derives status from a single
scalar, `net = received − refunded + adjusted`, against fixed thresholds.
Nothing constrains `received`/`refunded`/`adjusted` relative to each other, so:
a full refund of a fully-paid payment lands on `PENDING` — identical to
"never paid" (the `REFUNDED` enum value is never actually assigned by
`recompute_status`, only reachable via a raw admin edit that the next ledger
event silently overwrites); a pure goodwill write-off with zero cash received
reads as `PAID`; a single oversized refund event can jump a `PARTIALLY_PAID`
payment straight to `PENDING`, skipping past "untouched" even though real
money is sitting un-returned. None of this is currently caught anywhere in
`record_payment_event`.

**Fix** (per a formal pass over the arithmetic — see the PR review notes for
the full derivation): enforce two prefix constraints in
`record_payment_event`, checked before creating each new `PaymentEvent`:
1. cumulative `refunded ≤` cumulative `received` (can't refund unreceived money)
2. `received − refunded + adjusted ≤ amount` at every point (balance ≥ 0)

And reorder `recompute_status()` to check `refunded > 0 → REFUNDED` before
falling through to the `PAID`/`PARTIALLY_PAID`/`PENDING` split, so the
`REFUNDED` status becomes reachable and disjoint from the others. Treat this
as a floor-level sanity guard, not a full status-vocabulary redesign — the
team's own test (`test_expired_partially_paid_registration_cancels_but_
payment_stays_partial`) shows a deliberate preference for staff judgment over
automated correctness in this area, and that preference should stay intact.

**Touches:** `registrations/models.py` (`Payment.recompute_status`),
`registrations/services.py` (`record_payment_event`). Tests: extend
`registrations/tests_payment.py` with the refund-exceeds-received and
adjustment-only-with-zero-received cases.

### C2. Fix the `Payment.balance` docstring (bundle into C1) — DONE

The docstring says refund/adjustment "reduce and increase it respectively,"
which is backwards from both the code and the sentence right after it. Fix
while touching this code for C1.

## Phase D — optional, low priority, do opportunistically — DONE

- **D1. (DONE)** Narrow the promo-code redemption lock (`_resolve_promo_code`) from
  a `select_for_update()` held across the whole registration write to a
  single conditional `UPDATE ... WHERE uses_count < max_uses`. Only matters
  if a popular discount code (not a rare unlock code) sees real concurrent
  redemption volume.
- **D2. (DONE)** `Event.registration_window_status` can't distinguish a
  misconfigured window (`closes_at < opens_at`) from "not open yet" — add a
  `clean()` check.
- **D3. (DONE)** `_validate_ticket_type_for_attendee` compares against raw strings
  (`"child"`/`"parent"`/`"either"`) instead of the `AppliesTo` enum —
  readability nit, no behavior change.

## Explicitly not doing

Concurrent double-submission race (two near-simultaneous POSTs for the same
`(event, email)` before either verifies): not severe enough to warrant a DB
constraint right now — the existing "email matches a different family" guard
at verify time already catches the second one and routes it to
`pending_review` rather than double-confirming or double-charging, so B1
covers the cleanup path. `Registration.expires_at` being dual-purpose
(verification TTL vs. payment TTL) is a documented overload that works today
because both sweeps filter by status first; only worth splitting if a third
TTL-bound state gets added later.
