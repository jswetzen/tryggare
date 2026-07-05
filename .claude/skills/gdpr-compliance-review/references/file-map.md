# File Map — What This Review Touches

Mirrors the structure the original review brief used. Sections A–B are legal
documents; C–G are the backend/frontend code that implements what those
documents claim.

## A. Legal document templates (repo-tracked, public — should be 100% generic)

- `docs/legal/README.md` — index/overview of the legal docs.
- `docs/legal/DPA_TEMPLATE.md` — Art. 28 DPA template.
- `docs/legal/DPA_NOTE.md` — processor/sub-processor guidance notes.
- `docs/legal/DPIA_TEMPLATE.md` — Data Protection Impact Assessment template.
- `docs/legal/TECHNICAL_ANNEX.md` — infra/security detail backing the
  DPA/DPIA. History: this file has twice needed genericization commits after
  real facts crept in (see `recurring-incident-checklist.md`) — check the
  edits, not just the current text.
- `docs/legal/PRIVACY_POLICY_TEMPLATE.md` — parent/guardian-facing privacy
  notice.
- `docs/legal/TERMS_OF_SERVICE_TEMPLATE.md` — staff/operator-facing ToS.
- `docs/legal/LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md` — LIA for the
  legitimate-interest lawful basis.
- `docs/legal/BREACH_NOTIFICATION_PROCESS.md` — breach response process
  (controller-perspective only — see the routing table's note on the
  breach-sentinel skill for the missing processor-side runbook).
- `docs/roadmap/gdpr_compliance.md` — internal roadmap/status stub. Prone to
  staleness: check its claims (e.g. about consent fields, about a hosted
  offering being purely hypothetical) against current code/reality every
  time.

**Every `{{PLACEHOLDER}}` in every file in this section should be genuinely
generic.** Run `recurring-incident-checklist.md` against all of them.

## B. Real, non-generic legal drafts for a commercial/managed deployment (not in a fresh checkout)

If whoever runs this review also operates a commercial or managed deployment
of this software, real filled-in legal drafts (an actual DPA, commercial ToS,
technical annex with real infrastructure facts) may exist outside the tracked
repo — typically gitignored, since they carry facts that must never become
public. **Do not assume the public templates in Section A are a proxy for
these** — the templates are deliberately generic; the real drafts are where
infrastructure-truthfulness questions (encryption at rest, backup retention,
physical security) actually get resolved or not, and only reviewable if the
user supplies them directly.

Watch also for ad-hoc real-content files that are *not yet* gitignored — this
class of bug has happened before in this project (a filled-in draft left
untracked in the working tree). Check `git status` and `.gitignore` coverage
for anything under `docs/legal*` that contains real facts before assuming
the repo boundary is safe.

## C. Backend — retention & anonymization

- `backend/families/management/commands/anonymize_expired_data.py` — the
  actual retention/anonymization logic.
- `backend/families/apps.py` — scheduler wiring (`should_start_scheduler()`,
  `FamiliesConfig.ready()`), runs daily at 03:00.
- `backend/families/tasks.py` — `run_scheduled_retention` wrapper (invoked
  with `--include-audit-logs`).
- `backend/families/models.py` — `anonymized_at` fields on Family/Attendee.
- `backend/config/settings/base.py` — `DATA_RETENTION_DAYS` /
  `AUDIT_LOG_RETENTION_DAYS` (defaults 1095 days / 3 years each).
- `backend/families/tests_scheduler.py` — scheduler-guard unit tests.

## D. Backend — DSAR (data subject access/erasure requests)

- `backend/families/dsar.py` — `build_family_export`, `family_export_to_csv`,
  `scrub_family`, `scrub_audit_logs_for_children`.
- `backend/families/views.py` — `FamilyViewSet` export/erase actions.
- `backend/families/tests_gdpr.py` — the GDPR-specific test suite.

## E. Backend — audit logging

- `backend/checkins/audit.py` — `log_audit`, `get_client_ip`.
- `backend/checkins/migrations/0005_auditlog_user_nullable.py`
- `backend/checkins/migrations/0007_auditlog_session_id_auditlog_source_ip.py`

## F. Backend — Art. 9 health-data consent

- `backend/families/models.py` — `health_consent_status`/`_by`/`_at`/
  `_notice_version` fields on `Child`, including the `NEEDS_RECONFIRMATION`
  state logic in `Child.save()`.
- `backend/families/migrations/0012_add_anonymized_at_and_health_consent_fields.py`
- `backend/families/migrations/0013_backfill_health_consent_status.py`
- `backend/families/qr_views.py` — the **public, unauthenticated** QR lookup
  page. Check carefully that it doesn't surface health/consent data or
  anything else it shouldn't to an anonymous viewer.

## G. Privacy notice / public-facing

- `frontend/src/routes/privacy/+page.svelte`
- `frontend/src/lib/i18n/locales/en.json` / `sv.json` — the `privacy.*` keys
  actually shown to end users. **These can drift independently of
  `docs/legal/`** — always check both, in both languages (bilingual is a hard
  project requirement per this repo's CLAUDE.md).
- `backend/config/settings/base.py` — `DATA_CONTROLLER_NAME`/
  `_CONTACT_EMAIL`/`_URL`, `PRIVACY_POLICY_URL` env vars.
