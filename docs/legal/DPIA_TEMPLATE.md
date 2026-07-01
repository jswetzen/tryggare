# Data Protection Impact Assessment (DPIA) — {{ORGANISATION_NAME}}

*Template — complete and review before processing real children's data,
and keep it current as the system evolves. Last updated: {{DATE}}.*

A DPIA is required under GDPR Art. 35 whenever processing is likely to result
in high risk to data subjects — which applies here: systematic processing of
children's special-category health data (allergies/medical notes) at scale.
This is also the document IMY will ask for first if they ever look at this
system, and the one place to write down *why* the design choices below are
proportionate rather than leaving that reasoning implicit in the code.

This template is pre-filled with facts that are true of the software's
architecture regardless of who operates it. Replace `{{PLACEHOLDER}}` values
with your deployment's specifics.

---

## 1. Description of processing

**Nature:** A web application used by staff/volunteers to register children and
guardians, check children in and out of timed sessions, display safety-critical
alerts (allergies, medical notes) to staff and to whoever collects the child,
and print an identifying label with a QR code.

**Scope:** One {{ORGANISATION_NAME}} instance (single-tenant — see §4). Data
subjects: children attending events, and their parents/guardians. Approximate
volume: {{expected number of children per event / per year}}.

**Context:** Processing happens at in-person events (children's ministry,
Sunday school, conferences). Staff are {{employees / vetted volunteers}} of
{{ORGANISATION_NAME}}.

**Purpose:** Safeguarding — ensuring a child is only released to an authorised
guardian, and that staff have the safety information (allergies, medical
notes) they need during the event. This is the same purpose documented in
[`LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md`](LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md).

**Data processed:**

| Field | Data subject | Special category? |
|---|---|---|
| Name, date of birth | Child | No |
| Allergies, medical notes | Child | Yes — Art. 9 health data |
| Name, phone, email, relationship type | Guardian | No |
| Check-in/check-out timestamps, session, staff member | Child | No |
| Printed label (name + QR code only) | Child | No — see §5 on why health data is not printed |

**Data flow (lifecycle):**

1. Registration — staff enter child + guardian details (`FamilyViewSet.create`).
2. Check-in — child linked to a session; a short-lived, high-entropy QR code is
   allocated (`checkins/qr_utils.py`); staff/system broadcasts allergy/notes over
   the internal WebSocket channel for the check-in station.
3. During the event — staff view the family record (`GET /api/families/{id}/`,
   authenticated) or scan the QR code (`GET /api/qr/{code}/`, unauthenticated by
   design — see §4) to see the allergy alert at pickup.
4. Check-out — QR code enters a 24h grace period, then returns to the reuse pool.
5. Retention — `anonymize_expired_data` scrubs PII once a family has been
   inactive for `DATA_RETENTION_DAYS` ({{value}}, default 1095/3 years),
   keeping rows for aggregate/safeguarding integrity but removing name,
   allergies, notes, contact details.
6. Data subject rights — guardians can request export (`FamilyViewSet.export`)
   or erasure (`FamilyViewSet.erase`), both staff-initiated today.

See `docs/architecture.md` for the full system diagram.

---

## 2. Necessity and proportionality

- **Art. 6 basis:** Legitimate interests (safeguarding) — see the LIA.
- **Art. 9 condition:** {{vital interests, for the allergy/medical fields
  specifically — confirm with legal counsel; substantial public interest
  (safeguarding of minors) may also apply depending on jurisdiction}}.
- **Could the purpose be achieved with less data?** No — allergy/medical
  information is the specific field staff need to act on in an emergency;
  omitting it would remove the safety benefit that is the entire justification
  for processing it.
- **Is collection already minimised?** Yes, by construction: the printed label
  contains only the child's name and a QR code — no health data is rendered on
  a physical, unlogged printout. Health data only appears on authenticated
  screens or through the time-boxed QR flow described below.
- **Open question to resolve before commercial launch:** the QR-linked page
  (`qr_info`, §4) currently returns the guardian's email address alongside
  phone and name. Confirm whether email is operationally necessary on that
  specific surface (used for on-the-spot pickup matching) or whether it should
  be dropped from that response to tighten minimisation — phone/name are
  plausibly sufficient for the in-person matching use case.

---

## 3. Consultation

- **Stakeholders consulted:** {{pilot congregation staff, safeguarding lead,
  guardians if feasible}}.
- **Data Protection Officer / legal counsel consulted:** {{name, date}} — see
  `docs/legal-request-to-law-firm.md` for the parallel legal review in progress.
- **Views incorporated:** {{summarise any changes made as a result}}.

---

## 4. Data flow mapping and access points

| Access point | Auth | What it exposes |
|---|---|---|
| `FamilyViewSet` (admin UI) | Staff login, individual accounts (no shared/event passwords) | Full family record incl. allergies/notes |
| Check-in WebSocket broadcast | Staff login (station-scoped) | Allergies/notes for the checked-in child |
| Printed label | Physical possession | Name + QR code only |
| `GET /api/qr/{code}/` | **None (`AllowAny`)** | Allergies, notes, birthdate, guardian name/phone/email |
| DSAR export/erasure | Staff login | Full record, on request |

**Why the QR endpoint is unauthenticated (by design, not oversight):** it must
be usable by whoever is physically handed the label at pickup, without a staff
login. Mitigations: the code is only valid while the child is actively checked
in (data disappears from this surface within the grace period after
checkout); it is a 5-character code from a 32-symbol confusable-free alphabet
(~33.5M combinations); anonymous requests are throttled to 10/minute per IP.
Brute-forcing a single active code from one IP is impractical inside its
validity window; a distributed brute-force attempt is a residual risk (see §5).

**Tenant isolation:** each {{ORGANISATION_NAME}} instance is a separate
deployment — no cross-congregation data path exists at the application layer.

---

## 5. Risk identification and assessment

| # | Risk | Likelihood | Severity | Notes |
|---|---|---|---|---|
| R1 | QR code guessed/brute-forced from multiple IPs, exposing one child's health + guardian data | Low | High | Per-IP throttling only; a distributed attempt could evade it |
| R2 | Lost/discarded printed label read by an unauthorised person | Low | Low | Label carries no health data, only name + QR |
| R3 | Staff account compromise (credential theft, unattended session) | Low–Medium | High | Individual accounts; no shared logins |
| R4 | Insider misuse — staff browsing records without operational need | Low | Medium | Now mitigated by `record_viewed`/`qr_viewed` audit events (added {{DATE}}) |
| R5 | Data retained longer than necessary | Low | Medium | Automated `anonymize_expired_data`, but depends on the retention job actually being scheduled (cron/`make`) by the operator |
| R6 | Backup/export leakage | Low | Medium | {{describe backup encryption/access controls for your deployment}} |
| R7 | Guardian email over-collected relative to need on the QR surface | Medium | Low | See open question in §2 |

---

## 6. Mitigating measures already in place

- Individual staff accounts, no shared/event logins.
- Structured audit logging (`AuditLog`) covering both mutations (check-in,
  check-out, print, DSAR export/erasure) and read access (`record_viewed` on
  authenticated family views, `qr_viewed` on the anonymous QR endpoint),
  including `source_ip` and `session_id` for reconstruction of "who accessed
  what, from where, when."
- Automated retention/anonymisation (`anonymize_expired_data`), configurable
  via `DATA_RETENTION_DAYS` / `AUDIT_LOG_RETENTION_DAYS`.
- DSAR export and erasure tooling (staff-initiated today; see the roadmap for
  a self-service portal).
- QR code entropy + time-boxing + anonymous rate limiting (see §4).
- Printed labels carry no health data.
- Single-tenant-per-organisation architecture — no cross-tenant data path.
- TLS in transit ({{confirm your reverse-proxy/TLS termination setup}}).
- {{Encryption at rest for the database volume — operator responsibility;
  document your actual setup here}}.

## 7. Residual risk and sign-off

**Residual risk after mitigations:** {{Low / Medium — state your conclusion}}.

**Outstanding actions before go-live:**
- [ ] Resolve the guardian-email minimisation question in §2.
- [ ] Confirm the retention job is actually scheduled in production (cron/`make`).
- [ ] Document backup encryption and access controls (R6).
- [ ] Legal sign-off on the Art. 9 condition relied upon (§2).

**Assessed by:** {{NAME / ROLE}}
**Date:** {{DATE}}
**Next review:** {{DATE, or "before next material architecture change"}}
