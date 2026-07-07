# Self-Serve Event Registration & Mailing

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

## Dependencies

- SMTP relay + DPA in place before any real email goes out.
- Payment processing (or an explicit "free event" path) before
  registrations can be marked check-in-valid.

## Priority

Medium-high. The transactional-email half unblocks an existing
pre-launch legal gap regardless of what else in this doc gets built.
