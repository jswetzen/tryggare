# Payment Processing — Swish & Bankgiro (Manual Verification)

## Status (2026-07-09)

Phase 2 (this doc) is implemented on `feature/self-serve-registration`: a
`price` field on `Event`, a `Payment` model (`OneToOneField` to
`Registration`, reusing its `reference_code` rather than minting a new one),
Swish deep-link/QR construction (`registrations/swish.py`, no external API
call), three staff "mark as paid" Django admin actions
(Swish/Bankgiro/other), and a second scheduled sweep that cancels (never
deletes) verified-but-unpaid registrations after a 7-day payment TTL. The
`verify_registration` endpoint now routes a paid event's registration to
`pending_payment` instead of auto-confirming, with a public
`(reference_code, contact_email)`-keyed lookup endpoint for guardians who
navigate away before paying. No provider-interface abstraction was added
(see this doc's own "Future" section below) — both rails are 100%
manually verified in this phase, so there's nothing to abstract yet.

**Partial payments, overpayment, and refunds** (case catalog §5.1/§5.3,
punch-list item 7) are now also implemented: `Payment.status` gained
`partially_paid`, derived from a new append-only `PaymentEvent` ledger
(`registrations/models.py`) recording `received`/`refunded`/`adjustment`
entries against a Payment. `Payment.balance` is computed from the ledger;
`Payment.amount` itself still never changes after creation (it's set once
from `pricing.py::calculate_total()` — registration editing/repricing,
case catalog §8.2, is a separate, not-yet-built piece). Staff record
ledger entries one at a time via a dedicated `PaymentEventAdmin` (the
existing bulk "mark as paid" actions stay for the common one-shot full-
payment case, now recording a `received` event for the outstanding
balance under the hood). A registration only auto-confirms when the
ledger brings its balance to zero or below; a separate, explicitly
audited `confirm_despite_balance` staff action (case catalog §5.3: "de
betalar resten på lägret") confirms regardless of outstanding balance.
`payment_instructions()` (the Swish/Bankgiro guardian-facing payload) now
quotes the remaining balance, not the original nominal amount, so a
guardian returning to pay the rest isn't asked to pay twice. Not built:
a staff-facing outstanding-balances dashboard beyond Django admin, and
automatic balance-delta reminder emails — both layer cleanly on top of
the ledger later.

## Goal

Let congregations charge for paid events without Tryggare Moln ever
touching money movement, card data, or bank credentials — staff/finance
verify payment against a reference and mark it paid; Tryggare Moln only
ever records "paid" or "not yet."

## Why this design

Connecting to a payment gateway looks like the hard part, but Sweden's two
dominant consumer payment rails — Swish and Bankgiro — both work from a
**reference the payer types or scans**, which a human can verify without
any API integration. Staying manual-verification-only keeps Tryggare Moln
purely a data processor: no PSD2 / Finansinspektionen payment-institution
question ever arises, since no card data or payment execution touches the
system.

## Swish

- Use **Swish för föreningar** (the free/low-cost non-profit-association
  Swish number most Swedish banks offer), not Swish Handel/Företag
  (fee-bearing merchant product, per-transaction costs, certificate-based
  API) — a congregation almost certainly already has this or can get it
  trivially.
- QR generation needs **no external API call at all** — a Swish payment
  request is just a deep-link URL:
  `https://app.swish.nu/1/p/sw/?sw=<payee number>&amt=<amount>&cur=SEK&msg=<reference>&src=qr`.
  Tryggare Moln can construct this URL itself from the congregation's Swish
  number, the amount, and the reference code, then render it as a QR image
  with the same QR library already used for check-in codes
  (`qrcode` on the frontend / the Python equivalent on the backend). No
  Swish account credentials, certificate, or merchant agreement touch the
  app at all — it's just encoding a URL the payer's own Swish app opens.
- Swish's message field is short (~50 chars) and payer-editable — use it
  to carry a short reference code, don't rely on free-text name matching
  alone.

## Bankgiro

- No equivalent shortcut. True automatic reconciliation needs a
  **Bankgirot "Inbetalningar" file agreement through the congregation's
  own bank** — per-bank, per-customer, not a single integration Tryggare
  Moln can build once and reuse across congregations.
- Phase 1: fully manual. Staff checks the congregation's own online
  banking, matches the reference against the registration list, marks
  paid in Tryggare Moln.
- Phase 2 (optional, per-congregation): if a congregation's bank supports
  it, a periodic file import (staff-uploaded or SFTP-pulled) could
  semi-automate matching. Real integration work — evaluate only if a
  congregation actually asks for it.

## Reference numbers

Short and human-typeable, not a formal OCR/Luhn checksum — e.g.
`KL2026-0142` (event code + sequence). Easier for staff to eyeball-match
than a generated checksum number, and fits Swish's message field.

## Retention

Tryggare Moln's payment record is explicitly **not** the congregation's
accounting system of record — Bokföringslagen's 7-year retention is the
congregation's own bookkeeping's responsibility (their bank statements /
accounting software), not this app's. Tryggare Moln's payment record can
anonymize on the same schedule as the rest of the family's data.

## Future: real-time payment confirmation (research, not a commitment)

- **Swish Handel/Commerce API**: real and documented, supports
  payment-request creation plus webhook confirmation — but requires the
  congregation to hold the fee-bearing merchant product and a signed Swish
  certificate. The per-congregation single-tenant instance architecture
  helps here (each instance could hold its own certificate). Real dev
  effort: idempotent webhook handling, retry semantics, certificate
  lifecycle. Worth a dedicated spike once a congregation's volume
  justifies the cost — not before.
- Bankgirot file-based reconciliation (above) is the more realistic
  near-term automation path, since it doesn't require a new merchant
  agreement, just the file feed.

## Implementation sketch

### Data model

- Thin `Payment`-like record: amount, currency (SEK), method
  (`swish`/`bankgiro`/`manual_other`), reference code (generated by
  Tryggare Moln), status (`pending`/`paid`/`refunded`/`cancelled`),
  `paid_at`, `marked_by` (staff user). Tied to a registration grouping
  (see `event_registration_and_mailing.md`) rather than a single ticket,
  since a family registration is usually paid as one lump sum.
- Swish QR generation as a small service function, called when a
  registration is created for a paid event; embedded in the confirmation
  email alongside the Bankgiro number and reference as a fallback.

### Backend

- Staff-facing "mark as paid" action (admin or dedicated view), audited
  the same way check-in/checkout actions are.
- Ticket/registration only becomes check-in-valid once
  `Payment.status == paid`.

## Dependencies

- Registration flow (`event_registration_and_mailing.md`), or at minimum
  a manual-entry equivalent, needs to exist first to have something to
  attach a payment reference to.

## Priority

Medium. Real value once self-serve registration exists for paid events;
not useful in isolation.
