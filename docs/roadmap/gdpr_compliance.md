# GDPR Compliance — Follow-ups

## Goal

Core GDPR features are implemented (retention/anonymisation command, DSAR
export/erasure, public privacy page + notice, policy templates in
`docs/legal/`). This stub tracks the remaining, lower-priority hardening.

## How it works (current state)

- Retention: `anonymize_expired_data` management command, gated by
  `DATA_RETENTION_DAYS` / `AUDIT_LOG_RETENTION_DAYS`, run via cron.
- DSAR: `FamilyViewSet` `export`/`erase` actions + Django Admin actions.
- Privacy: `/api/privacy/` endpoint + `/privacy` frontend page, controller
  details from `DATA_CONTROLLER_*` env vars.

## Follow-ups

### Scheduled-job runner
The retention command relies on an operator-configured cron entry. Consider an
in-app scheduler (Celery beat — Channels/Redis is already present, or a
management-command-on-boot) so self-hosters don't have to wire cron themselves.

### Encryption at rest
Currently an operator/infrastructure responsibility, documented but not enforced.
Add deployment guidance (or a startup check) verifying the database volume is
encrypted.

### Self-service DSAR portal
Today DSAR export/erasure is staff-initiated. A future flow could let a
parent/guardian request their data via a verified link.

### Consent basis (only if needed)
The system relies on legitimate interest, so there are no consent fields. If a
future use case needs consent as the basis, add consent capture + a consent
audit trail.

### SaaS processor tooling
When the hosted offering lands: per-tenant data isolation review, sub-processor
list surfacing, and a controller-facing DPA (see `docs/legal/DPA_NOTE.md`).

## Priority

Low / opportunistic. The compliance baseline is in place; these are hardening
and convenience items.
