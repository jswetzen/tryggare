# The Art. 9 Legal Basis — Canonical Reasoning

**This is the single most important fact in this skill.** It has been derived
correctly once, shipped, and then silently reverted by an unrelated git
history rewrite. Treat any Tryggare legal document that contradicts this file
as regressed, not as a legitimate alternative interpretation, unless the user
has explicitly told you the reasoning changed.

## The three-layer structure

Tryggare processes three tiers of personal data about children/guardians at
church/organisation events, each needing its own GDPR Art. 6 + (where
applicable) Art. 9 basis. All three layers must appear **consistently** across
every document that states a legal basis: the privacy policy, the LIA, the
DPIA §2, both DPAs (template and any real filled draft), and any live
product-facing string (e.g. `frontend/src/lib/i18n/locales/{en,sv}.json`
`privacy.legalBasis`).

### Layer 1 — ordinary data → Art. 6(1)(f) legitimate interest

Names, contact details, check-in/check-out timestamps, attending staff member,
QR/label history. Basis: **legitimate interest (safeguarding)** —
Art. 6(1)(f), documented in the LIA with a genuine three-part test (purpose,
necessity, balancing) that gives children's interests specific weight
(Recital 38), not a pre-filled "Low impact" conclusion.

### Layer 2 — allergy/medical notes → Art. 9(2)(a) explicit consent, NOT vital interests

Allergy and medical-note fields are Art. 9 special-category (health) data.
The **correct** basis is **explicit guardian consent (Art. 9(2)(a))**:
- Captured at registration as a separate, optional, unticked step.
- Attendance is **never** conditional on giving it.
- Withdrawable at any time (Art. 7(3)) without affecting attendance.

**Vital interests (Art. 9(2)(c)) is the wrong basis for collecting this
data**, and this is the error that keeps recurring in the docs. 9(2)(c)
applies only where the data subject is *incapable* of consenting — genuine
emergencies (unconsciousness, incapacity). Here, the guardian fills in the
data calmly, in advance, at registration — the opposite situation. Both IMY
and the EDPB read this exception narrowly; a supervisory authority would
reject it. Vital interests **does** remain the correct basis for *using* the
already-collected data in an actual emergency at pickup/on-site — that's a
separate, narrower claim than the collection basis.

**Substantial public interest (Art. 9(2)(g)) also does not work** as an
alternative or fallback: it requires a basis in Union or Member State law,
and Dataskyddslagen (the Swedish GDPR-implementing act) provides no such
basis for private-sector safeguarding of this kind. If you see 9(2)(g)
proposed anywhere in these docs, that's also wrong, not a legitimate
alternative to 9(2)(a).

### Layer 3 — attendance / religious affiliation → Art. 9(2)(d)

The mere fact of attendance at a church/congregation's activities can itself
reveal religious belief, which is also Art. 9 special-category data — a
separate dimension from the health data above, and not covered by the LIA
(which only carries ordinary Layer-1 data). The correct basis is
**Art. 9(2)(d)**: religious non-profits may process such data about their own
members and people in regular contact, provided it isn't disclosed externally.

## Why this matters more than it looks

- **It has already regressed once.** A branch that fixed this correctly
  (rewriting `DPIA_TEMPLATE.md` §2, `LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md`,
  `PRIVACY_POLICY_TEMPLATE.md`, and the DPA open-questions section) was later
  rebuilt via `git filter-repo`/history rewrite to purge unrelated leaked PII,
  and the Art. 9 fix silently disappeared in the process — the rewrite base
  predated the fix. **Always diff the current state of these four documents
  against this file's Layer 2/3 description before concluding the basis is
  correctly stated**, rather than trusting that a prior review's fix is still
  present.
- **A real external reviewer (a law firm, in a simulated but methodologically
  real review) independently reached the exact same conclusion**, including
  the same three-layer split and the same rejection of vital interests and
  substantial public interest — this is not a idiosyncratic interpretation,
  it is the position a real Swedish data-protection lawyer would take.
- **The live product string can drift independently of the docs.** Check
  `frontend/src/lib/i18n/locales/en.json` / `sv.json`, key `privacy.legalBasis`
  (and any adjacent `privacy.rights` withdrawal-right string) — these are
  separate from `docs/legal/` and have been found stating "vital interests"
  even when the legal docs said something else. Both must be fixed together.

## Consent implementation status (code side)

As of the last review, the *code* correctly implements consent capture
independently of the doc wording (the doc regression above is a
documentation/product-copy problem, not a code problem — check both, they can
be out of sync in either direction):

- `Child.health_consent_status` — enum: `not_applicable` / `granted` /
  `declined` / `withdrawn` / `needs_reconfirmation`.
- `Child.save()` enforces an invariant: health text may only be present
  alongside `granted` or `needs_reconfirmation` — any other status gets
  quarantined into `needs_reconfirmation` rather than trusted, protecting
  against bulk imports / admin edits / stale data silently looking approved.
- A migration back-filled all pre-existing (pre-consent-UI) health data into
  `needs_reconfirmation` rather than assuming past paper/verbal process
  satisfied Art. 9(2)(a) — this is the right call, verify it wasn't reverted.
- **Still open, verify current status**: the withdrawal *path* itself (model
  supports `withdrawn` but no UI/endpoint triggers it), the staff-facing
  reconfirmation banner for `needs_reconfirmation` records, and whether data
  in that quarantined state is still displayed identically to fully-consented
  data on authenticated views and the public QR endpoint (it should arguably
  be flagged differently, or at minimum this should be a documented decision
  in the DPIA rather than an accident).
