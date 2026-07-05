# GDPR Compliance — Follow-ups

## Goal

Core GDPR features are implemented (retention/anonymisation command, DSAR
export/erasure, public privacy page + notice, policy templates in
`docs/legal/`). This stub tracks the remaining, lower-priority hardening.

## How it works (current state)

- Retention: `anonymize_expired_data` management command, gated by
  `DATA_RETENTION_DAYS` / `AUDIT_LOG_RETENTION_DAYS`, run automatically every
  day at 03:00 by an in-app `apscheduler` `BackgroundScheduler` started from
  `families/apps.py` (`FamiliesConfig.ready()`), which calls the thin task
  wrapper in `families/tasks.py` (`run_scheduled_retention`, invoked with
  `--include-audit-logs` so audit logs are pruned too). No operator-configured
  cron entry required — self-hosters get retention enforcement out of the box.
  The scheduler only starts in the actual server process (daphne), not during
  `manage.py test`/`migrate`/`shell`/etc.; see `should_start_scheduler()` in
  `families/apps.py` for the guard and its rationale.
- DSAR: `FamilyViewSet` `export`/`erase` actions + Django Admin actions.
- Privacy: `/api/privacy/` endpoint + `/privacy` frontend page, controller
  details from `DATA_CONTROLLER_*` env vars.

## Follow-ups

### Encryption at rest
Currently an operator/infrastructure responsibility, documented but not enforced.
Add deployment guidance (or a startup check) verifying the database volume is
encrypted.

### Self-service DSAR portal
Today DSAR export/erasure is staff-initiated. A future flow could let a
parent/guardian request their data via a verified link.

### Consent basis (health data)
Ordinary data relies on legitimate interest (6(1)(f)); allergy/medical fields
are special-category data and require explicit guardian consent (9(2)(a)) —
implemented: a staff-attested consent checkbox in the registration UI, a
`health_consent_status` enum (`not_applicable`/`granted`/`declined`/`withdrawn`/
`needs_reconfirmation`) enforced by a `Child.save()` invariant, and a
notice-version stamp (`HEALTH_CONSENT_NOTICE_VERSION`) recorded per consent.
Pre-existing (pre-consent) health text is quarantined into
`needs_reconfirmation` rather than assumed granted. Still open: no guardian
self-service withdrawal path (withdrawal today is staff-mediated), and no
staff-facing banner surfacing children in `needs_reconfirmation` so the
quarantine is actionable rather than silent.

### SaaS processor tooling
The hosted offering has live pilots today, not just a future plan — per-tenant
data isolation review, sub-processor list surfacing, and a controller-facing
DPA (see `docs/legal/DPA_NOTE.md`) are active, near-term work, not
speculative.

## Priority

Low / opportunistic. The compliance baseline is in place; these are hardening
and convenience items.
