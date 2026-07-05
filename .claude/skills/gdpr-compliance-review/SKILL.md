---
name: gdpr-compliance-review
description: >
  Independently assess whether this project's GDPR compliance work
  (docs/legal/* templates + the backend code that implements
  retention/DSAR/audit/consent) is actually sound — both the legal
  documentation itself and whether the code genuinely implements what the
  documentation claims. Routes to the bundled Lawvable legal skills per
  document type, and carries this project's own accumulated GDPR domain
  knowledge forward so a review can start immediately without re-deriving it.
  Use when asked to review GDPR/legal compliance, audit docs/legal/, check the
  DPA/DPIA/privacy policy/breach process, or redo a prior legal review.
metadata:
  author: "Johan Swetzén (project skill, compiled from a 2026-07-04 review)"
  scope: "check-ins / Tryggare"
  type: "project orchestrator skill"
---

# Tryggare GDPR Compliance Review

This skill is the entry point for reviewing Tryggare's GDPR compliance work.
It does not replicate the underlying legal skills — it routes to them (all
bundled alongside this skill under `.claude/skills/`) and supplies the
project-specific facts, history, and recurring failure modes a fresh review
would otherwise have to rediscover from scratch.

**Read `references/art9-legal-basis.md` before touching any Art. 9 content,
in any document.** This is the single most important and most-regressed
piece of domain knowledge in this project — see "Why this skill exists" below.

## Why this skill exists

A prior review (2026-07-04) found the compliance work was strong overall but
caught two classes of recurring problems that a from-scratch review would
waste time rediscovering:

1. **A specific legal-basis error keeps coming back.** The correct three-layer
   Art. 9 reasoning (see `references/art9-legal-basis.md`) was derived once,
   written into the docs, and then **silently reverted** by an unrelated git
   history rewrite (the rewrite was purging leaked real-world facts and
   clobbered the legal-basis fix as collateral damage). Any time you review
   this project's Art. 9 material, check whether it still says "vital
   interests" for the health-data basis — if so, that's not a fresh finding,
   it's the same regression happening again.
2. **Real, identifying business facts leak into the generic public templates.**
   This has happened twice: once with a real city/name/company hardcoded into
   `TECHNICAL_ANNEX.md`, purged via history rewrite; separately, a real filled
   legal-review document was left untracked and un-gitignored, one `git add -A`
   away from the public repo. Every review must include the sweep in
   `references/recurring-incident-checklist.md`.

## Objective

This is a **real compliance review**, not a code-style review. The questions
that matter: *is this true, is this complete, would it hold up if a regulator
or a customer's DPO actually read it.* Rank findings by severity: a real
compliance/legal gap or data leak first, then correctness bugs in the GDPR
mechanisms, then doc/code inconsistencies, then nice-to-haves. Each finding
needs the specific file (and line where applicable) and a one-sentence
description of the concrete problem — not "this could be clearer."

## Scope — load `references/file-map.md` first

That file lists every file this review touches, grouped into:
- **A** — generic public templates (`docs/legal/*_TEMPLATE.md`, `README.md`,
  `BREACH_NOTIFICATION_PROCESS.md`) — must be 100% generic, no real facts.
- **B** — any real, non-generic filled-in legal drafts for a commercial or
  managed deployment (gitignored where they exist) — only reviewable if the
  user supplies them; they live outside a fresh checkout.
- **C–G** — backend code: retention/anonymization, DSAR, audit logging,
  Art. 9 consent, and the public-facing privacy notice/QR page.

Also check `docs/roadmap/gdpr_compliance.md` for staleness against whatever
the code currently does — it's a stub, easy to let drift.

## Routing — which bundled skill to use for which file

| Target | Skill to load | Mode / focus |
|---|---|---|
| `docs/legal/DPA_TEMPLATE.md`, `DPA_NOTE.md`, any real filled-in DPA draft | `dpa-art-28-oliver-schmidt-prietz` | `REVIEW_QUICK` for a sign/no-sign pass, `REVIEW_NEG` if negotiating with a real counterparty. Run the Art. 26 joint-controller screen first (single-tenant, not JC — should clear quickly), then the Art. 28(3)(a)–(h) checklist. |
| `docs/legal/DPIA_TEMPLATE.md` | `dpia-sentinel-oliver-schmidt-prietz` | Threshold check is almost academic here — children + Art. 9 health data at scale trips Art. 35(3)(b) directly. Focus effort on the risk register (5×5, Track A/B) and whether mitigations map to real code, not on re-litigating whether a DPIA is required. |
| `docs/legal/PRIVACY_POLICY_TEMPLATE.md`, `frontend/src/routes/privacy/+page.svelte`, `frontend/src/lib/i18n/locales/{en,sv}.json` (`privacy.*` keys) | `gdpr-privacy-notice-eu-oliver-schmidt-prietz` | Notice type = **Website/App** section map, but cross-check against the **B2C/Employee** intake groups for the staff ToS. Run the Art. 13/14 mandatory-disclosures checklist in that skill's `EU_COMMON.md`. No jurisdiction file for Sweden exists in that skill — don't load DE/FR/OTHER_EU, they don't apply. |
| `docs/legal/BREACH_NOTIFICATION_PROCESS.md` | `gdpr-breach-sentinel-oliver-schmidt-prietz` | This is a **controller-perspective** process only. For any hosted/managed deployment run as a processor relationship, a **processor-side** runbook is still missing (notify every affected customer within the promised window, then help each with its own supervisory-authority assessment) — flag as a gap, don't assume the existing doc covers it. |
| `docs/legal/TERMS_OF_SERVICE_TEMPLATE.md`, any real commercial-ToS draft, general clause-by-clause pass on any doc | `dpdpa-gdpr-review-parth-desai` | Ignore the DPDPA (India) half entirely — use only the GDPR checklist and model clauses. Good for a fast compliant/at-risk/non-compliant flag pass before a deeper skill-specific review. |
| `backend/families/dsar.py`, `management/commands/anonymize_expired_data.py`, `apps.py`, `tasks.py`, `checkins/audit.py` | `compliance-anthropic` (Privacy Compliance Advisor) | Its DPA-review checklist and DSAR-handling checklist are the right lens for "does the code actually do what the docs claim" — pair with direct code reading, this skill alone won't read the repo for you. |
| **LIA** (`LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md`), retention-period reasoning, TOMs (`TECHNICAL_ANNEX.md`), anything Sweden-specific (IMY, Dataskyddslagen) | **No bundled skill covers this** | Reason from `references/art9-legal-basis.md` and GDPR first principles directly. See "Gaps" below. |

## What to actually check (carry this checklist into every review)

- [ ] For every `{{PLACEHOLDER}}` in every Section-A file: is it genuinely
      generic, or does it (still) contain a real fact that should be a
      placeholder? Run `references/recurring-incident-checklist.md`.
- [ ] For each implemented mechanism (retention, DSAR, audit, consent): does
      the code actually do what the docs claim end-to-end — not "a command
      exists" but "it's actually scheduled and actually runs." Check the
      scheduler guard in `families/apps.py` (`should_start_scheduler()`)
      isn't accidentally disabled in production.
- [ ] Does DSAR erasure (`scrub_family`) cover every field DSAR export
      (`build_family_export`) reveals? Anything exported but not erasable?
      (Known past finding: `external_booking_id` was exported but never
      scrubbed — re-verify, don't assume it's still broken or still fixed.)
- [ ] Is the audit log itself in scope for retention, or does it retain PII
      indefinitely regardless of the family/child retention window? Check
      whether erasure audit-log entries (`dsar_erasure` action) themselves
      carry PII in `details` that the scrubber can't reach.
- [ ] Does `qr_views.py` (or wherever the public unauthenticated QR endpoint
      lives) leak health-consent status, audit history, or any other
      sensitive field to an anonymous viewer? Also check whether data in a
      `needs_reconfirmation` consent state is still displayed as if consent
      were fully valid.
- [ ] Cross-check the DPA's sub-processor list against the Technical Annex's
      infrastructure section — the templates instruct authors to keep these
      consistent; do they actually agree as currently written?
- [ ] Is `docs/roadmap/gdpr_compliance.md` stale relative to the actual code
      (e.g. does it still say "no consent fields" after consent fields shipped)?
- [ ] Any other real names, addresses, phone numbers, pricing, or specific
      customer/organisation names baked into files that are supposed to stay
      generic?

## Before concluding — check `references/known-gaps.md`

That file tracks the gap history (B1–B4, M1–M11 in the numbering used
internally) as of the last review, with status. **Don't treat a known,
already-flagged gap as a fresh discovery** — instead verify whether it's
still open, was fixed, or regressed. Update your findings to say which.

## Reporting format

Findings ranked by severity: real compliance/legal gap or data leak first,
then correctness bugs in the GDPR mechanisms, then doc/code inconsistencies,
then nice-to-haves. Each with the specific file (and line where applicable)
and a one-sentence description of the concrete problem.

## Section B — real, non-generic drafts for a commercial/managed deployment

If whoever runs this review also operates a commercial or managed deployment
of this software, real filled-in legal drafts (an actual DPA, commercial ToS,
technical annex with real infrastructure facts) may exist outside the tracked
repo — typically gitignored, since they carry real company/infrastructure
details that must never become public. These are out of scope for a review
based on the tracked repo alone. If you need to assess their actual content,
ask the user to supply it directly rather than assuming the generic templates
stand in for it — the templates are deliberately generic, and the real drafts
are where infrastructure-truthfulness questions (encryption at rest, backup
retention, physical security) actually get resolved or not. Never write real
facts from those drafts into this skill file or its siblings.

## Gaps — no bundled skill covers these; reason from first principles

Confirmed by catalogue search: there is no Sweden-tagged legal skill, and no
skill specifically covers the **LIA / Art. 6(1)(f) balancing test**, **Art. 9
health-data consent for children** beyond generic checklists, **retention /
storage-limitation wording** (the backup-expiry problem), **Art. 32 TOMs**
depth, or **Swedish specifics** (IMY as supervisory authority, Dataskyddslagen
having no private-sector safeguarding basis under Art. 9(2)(g)). For these,
use `references/art9-legal-basis.md` and the GDPR text/EDPB guidance directly.
