# Known Gap History — Verify Status, Don't Rediscover

This tracks the gap numbering used internally across prior reviews (B1–B4 =
blockers, M1–M11 = important-before-wider-rollout, G1–G6 = missing documents).
The numbering is not in the repo itself — it exists only in review history.
**On each new review, re-verify each item's current status rather than
treating it as either "already handled" or "a fresh finding."** Status below
is as of the last full review (2026-07-04); it will have moved on.

## Blockers (B1–B4)

- **B1 — Art. 9 legal basis wrong (vital interests instead of consent).**
  See `art9-legal-basis.md` for the full reasoning. Status history: fixed
  once across the LIA/DPIA/privacy-policy/DPA docs → **silently reverted** by
  an unrelated history rewrite that purged leaked PII → as of the last check,
  still wrong in the docs (and in the live `en.json`/`sv.json` product
  strings) even though the *code* correctly implements consent capture
  independently. Re-check the current text of all four documents plus the
  live locale strings every time; do not assume a prior fix is still present.
- **B2 — Staff/volunteers missing as data subjects in the DPA(s).** The DPA's
  data-subject-categories section (§3) must list staff/volunteer accounts and
  audit logs (user, source IP, session id) alongside children and guardians —
  this data genuinely is processed on the controller's behalf. Was fixed once
  alongside B1, subject to the same reversion risk — re-check.
- **B3 — Backup retention/deletion wording vs. reality.** A DPA promising
  deletion "including backups" within a fixed post-termination window is only
  honest if the actual backup infrastructure enforces a bounded rotation —
  check whether that's actually configured, not just documented as a
  `{{CONFIRM}}` placeholder. **This is potentially a real, unresolved
  operational gap, not just a wording problem**: don't "resolve" an open
  placeholder by inventing a plausible-sounding number — verify a real
  rotation policy is configured, that the technical annex's wording matches
  it (stating the actual computed worst-case ceiling, not just one tier's
  count), that the DPA's termination clause is consistent with that ceiling
  (see the backup-exemption pattern in `DPA_TEMPLATE.md` §10.1a) rather than
  promising something the infrastructure can't keep, and that a backup
  restore has actually been tested (an untested backup is not a control).
- **B4 — Encryption-at-rest / infra claims not yet confirmed true.** Check
  whether the Technical Annex still correctly distinguishes "planned" from
  "confirmed live in production" for its encryption-at-rest claims, rather
  than asserting something unverified as fact. Also check physical/access
  security of the hosting setup is described at a level of detail
  proportionate to what's actually needed (a controller's board or a
  supervisory authority would ask about physical access controls, power
  redundancy, and hardware-failure handling) without over-disclosing specific
  infrastructure facts in a document meant to stay generic.

## Important-before-wider-rollout (M1–M11)

- **M1 — No third-country transfer clause.** Trivially true today (everything
  in Sweden/EU) — but Art. 28(3)(a) requires the clause to exist regardless.
  Cheap to add; check it's actually there.
- **M2 — Art. 28(3)(f) only half-covered.** Breach assistance is present;
  assistance with DPIAs (Art. 35) and prior consultation (Art. 36) may still
  be missing — one sentence fixes it if so.
- **M3 — Audit-log retention wording understates the code.** The docs may
  still call audit-log pruning "optional" when the scheduled job always
  passes `--include-audit-logs` (verify in `families/tasks.py`) — i.e.
  pruning is actually automatic and daily. This is a doc-undersells-code
  case, not a compliance gap, but should be fixed for accuracy.
- **M4 — Cross-references pointing at the wrong/generic document.** The real
  Villkor/DPA sometimes reference the generic template files (`DPA_TEMPLATE.md`,
  `DPIA_TEMPLATE.md`) by filename instead of the real filled counterparts, or
  reference "docs/legal-request-to-law-firm.md" which may not exist under
  that name. Repo filenames also don't belong in signed contracts — check
  whether a numbered-annex restructure (Villkor + Bilaga 1/2/3) has happened.
- **M5 — Villkor missing standard commercial clauses**: customer's own
  responsibility as controller, "customer's data belongs to the customer",
  force majeure, and a supplier-continuity/exit clause (the AGPL angle: if the
  operator disappears, the customer can legally self-host the same software —
  this is a genuine selling point worth writing in explicitly, not just an
  implicit fact).
- **M6 — Hardware sale (print-hub device) has no terms.** Warranty/DOA
  handling, who patches the device OS, and whether the operator has remote
  network access to maintain it (if so, that access path belongs in the
  technical annex/TOMs).
- **M7 — QR endpoint guardian-email overexposure.** Was flagged as a DPIA risk
  (over-collection on the anonymous QR surface), then fixed in code (email
  dropped from the response). Re-verify the fix is still in place and that
  DPIA risk-register entries referencing it have been updated to reflect the
  fix, not left describing the old behavior.
- **M8 — Breach process is controller-perspective only.** A processor-side
  runbook (notify every affected customer/congregation within the committed
  window, then help each with its own 72h supervisory-authority assessment)
  is still needed for any hosted/managed deployment run as a processor
  relationship. Also worth a conscious, documented choice of the
  processor→controller notification window (e.g. 24h vs. 48h) that's
  realistically achievable given actual operational capacity, while staying
  safely inside the controller's own 72h deadline — don't let an aspirational
  number go unquestioned.
- **M9 — Privacy policy Art. 13 completeness.** Beyond B1: for hosted
  deployments the processor should be explicitly named; if import
  integrations (e.g. FestivalPro/Planning Center) are used, Art. 14 disclosure
  of the data source is required since data isn't collected directly from the
  data subject; confirm the app sets only strictly-necessary session cookies
  (avoids needing a cookie-banner at all).
- **M10 — DPA term not coterminous with the commercial ToS/Villkor.** A DPA
  with independent termination language can create the forbidden state
  "service continues, DPA terminated." This was fixed once (DPA lifetime tied
  explicitly to the Villkor's) — re-verify it's still tied together and
  wasn't reverted alongside B1/B2.
- **M11 — LIA pre-fills its own conclusion.** The balancing-test table should
  not ship with "Impact on individuals: Low" already concluded for children's
  health-adjacent data — that's for each controller to assess, and Recital 38
  (children merit specific protection) should appear as an explicit factor,
  not be implicit.

## Missing documents (G1–G6)

1. **Art. 30 records of processing** — missing entirely, and mandatory (the
   Art. 30(5) small-enterprise exemption does not apply: processing is
   regular, not occasional, and includes Art. 9 data). Needs both a
   controller-facing template (for congregations) and the operator's own
   processor-side version.
2. **Consent form/wording for guardians** — the exact text shown at
   registration, EN + SV, versioned (the version string is what a consent
   record points at — check `HEALTH_CONSENT_NOTICE_VERSION` /
   `health_consent_notice_version` actually get bumped when wording changes).
3. **Child-friendly notice** — Art. 12 age-appropriate transparency; a short,
   plain "what we know about you and why" aimed at children themselves.
4. **Processor-side incident runbook** — see M8.
5. **DPO assessment note** — one paragraph documenting why neither party
   requires a DPO under Art. 37 (small scale per controller, not "large
   scale" core activity) — pre-empts the question rather than leaving it
   unaddressed.
6. **Congregation onboarding checklist** — sign Villkor + annexes, publish
   privacy policy, adopt LIA + DPIA as their own, set the `DATA_CONTROLLER_*`
   / `DATA_RETENTION_DAYS` env vars to match the published policy, collect
   consent forms. The pieces exist in prose across `docs/legal/README.md`;
   turning it into an actual checklist makes it operational.

## Correctness bugs found in the GDPR mechanisms (verify current status)

- `scrub_family` did not clear `Family.external_booking_id` — a unique
  identifier mapping an "anonymized" row back to a full-PII record in an
  external import system (FestivalPro/Planning Center), and the field *is*
  included in the DSAR export. Re-check whether this is fixed.
- The `dsar_erasure` audit-log entry stored `family.last_name` in `details`,
  under a key the audit-log PII scrubber doesn't know about and on an
  `entity_type` the scrubber's child-id filter can't match — meaning an
  erasure could leave PII sitting in the audit log for the full retention
  window. Re-check whether this is fixed.
- `Child.save()`'s consent-quarantine invariant can be silently defeated if a
  caller saves with an explicit `update_fields` list that includes the text
  fields but not `health_consent_status` — the in-memory flip to
  `needs_reconfirmation` never gets persisted. Re-check call sites.
