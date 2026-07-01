# Data Processing Agreement (DPA / Personuppgiftsbiträdesavtal) — {{ORGANISATION_NAME}}

*Template — complete and have reviewed by a lawyer before signing. Applies to
the hosted/SaaS scenario described in [`DPA_NOTE.md`](DPA_NOTE.md) §2: a
third party (the "Processor") operates Tryggare on behalf of an organisation
(the "Controller"). If you self-host with no third-party operator, you don't
need this document — see `DPA_NOTE.md` §1. Last updated: {{DATE}}.*

---

**between**

**{{CONTROLLER_NAME}}** ("the Controller" / *personuppgiftsansvarig*)

**and**

**{{PROCESSOR_NAME}}**, org./reg. no. {{PROCESSOR_ORG_NUMBER}} ("the
Processor" / *personuppgiftsbiträde*)

---

## 1. Background and purpose

1.1 The Controller is responsible for children and their guardians attending
its events, and processes personal data about them, including special
category data (health data within the meaning of GDPR Art. 9 — allergies and
medical notes).

1.2 The Controller has engaged the Processor to provide the Tryggare child
check-in service.

1.3 This Agreement governs the Processor's processing of personal data on the
Controller's behalf in accordance with GDPR Art. 28.

---

## 2. Subject matter, duration and purpose

2.1 **Subject matter:** the Processor processes personal data on the
Controller's behalf within the Tryggare service, as described in this
Agreement and the technical documentation referenced in §6.3.

2.2 **Purpose:** solely to provide the Tryggare service to the Controller,
comprising:

- Registration and storage of child and guardian records
- Check-in/check-out of children to timed sessions
- Display of safety-relevant information (allergies, medical notes) to
  Controller staff and, via the printed-label QR flow, to whoever collects a
  checked-in child
- Data-subject-rights support (export, erasure) on the Controller's instruction
- Automated retention/anonymisation per §9

2.3 **Duration:** from signature until terminated with {{NOTICE_PERIOD, e.g.
three (3) months}} notice. On termination, §10 applies.

---

## 3. Type of personal data and categories of data subjects

3.1 **Categories of data subjects:** children attending the Controller's
events; their parents/guardians.

3.2 **Types of personal data:**

- Child: first name, last name, date of birth, allergies, free-text
  medical/behavioural notes
- Guardian: name, phone number, email address, relationship to the child
- Operational: check-in/check-out timestamps, session, attending staff
  member, printed-label/QR history

3.3 Allergy and medical-note fields are **special category data (health
data)** under GDPR Art. 9. The Processor acknowledges the heightened duty of
care this requires.

---

## 4. Processor's obligations

The Processor shall:

a) process personal data only on the Controller's documented instructions and
not for its own purposes;

b) ensure that personnel with access to the data are bound by confidentiality
obligations;

c) implement the technical and organisational measures described in §6;

d) assist the Controller in responding to data-subject-rights requests (§7);

e) assist the Controller with personal data breach notifications (§8);

f) delete or return personal data on termination (§10);

g) make available the information necessary to demonstrate compliance and
allow for audits (§11);

h) inform the Controller promptly if, in the Processor's assessment, an
instruction from the Controller would infringe applicable data protection law.

---

## 5. Sub-processors

5.1 As of {{DATE}}, the Tryggare service runs on infrastructure operated
directly by the Processor (self-hosted) with **no third-party sub-processor**
handling personal data. If this changes (e.g. a transactional email provider,
managed hosting), the table below is updated and the Controller notified per
§5.2 before the change takes effect.

| Sub-processor | Purpose | Data categories | Location |
|---|---|---|---|
| {{none as of DATE — update when applicable}} | | | |

5.2 The Processor shall give the Controller at least {{30}} days' written
notice of any new or replacement sub-processor, during which the Controller
may object. If the parties cannot resolve an objection, the Controller may
terminate this Agreement without penalty.

5.3 The Processor remains fully liable to the Controller for any
sub-processor's processing of personal data.

---

## 6. Technical and organisational security measures

6.1 The Processor shall implement and maintain appropriate technical and
organisational measures against unauthorised or unlawful processing, and
against accidental loss, destruction or damage, proportionate to the risk and
sensitivity of the data (GDPR Art. 32).

6.2 Measures currently implemented:

- TLS in transit ({{describe reverse-proxy/TLS termination}})
- Individual staff accounts — no shared or "event password" logins
- Role-scoped authentication on all endpoints except the single unauthenticated
  QR-lookup endpoint, which is intentionally time-boxed and rate-limited (see
  the DPIA §4 for the reasoning)
- Structured audit logging of both data mutations (check-in, check-out,
  label print, export, erasure) and record access/views, capturing user,
  source IP, and session — see `checkins/models.py` `AuditLog`
- Automated retention/anonymisation (`anonymize_expired_data`, driven by
  `DATA_RETENTION_DAYS` / `AUDIT_LOG_RETENTION_DAYS`)
- {{Database encryption at rest — describe your actual setup}}
- {{Backup encryption and access controls — describe your actual setup}}

6.3 Further detail is available on request in a technical annex (architecture
documentation, `docs/architecture.md`, and the DPIA at
[`DPIA_TEMPLATE.md`](DPIA_TEMPLATE.md)), treated as confidential by the
Controller.

---

## 7. Data subject rights

7.1 The Processor shall, on the Controller's request, assist in responding to
data subjects exercising their rights of access, rectification, erasure,
restriction, portability and objection.

7.2 In practice: the Controller (via authorised staff) can self-serve export
(`GET /api/families/{id}/export/`) and erasure
(`POST /api/families/{id}/erase/`) — both authenticated, staff-attributed, and
audit-logged.

7.3 The Processor shall not respond directly to a data subject without the
Controller's instruction, unless required by law.

---

## 8. Personal data breaches

8.1 The Processor shall notify the Controller without undue delay, and no
later than **{{24}} hours** after becoming aware of a personal data breach,
per the process in
[`BREACH_NOTIFICATION_PROCESS.md`](BREACH_NOTIFICATION_PROCESS.md). The
notification shall include, to the extent known: the nature of the breach,
categories/approximate number of data subjects and records affected, likely
consequences, and measures taken or proposed.

8.2 The Controller is responsible for notifying the supervisory authority
(IMY) within 72 hours under GDPR Art. 33, and data subjects under Art. 34
where required.

8.3 The Processor shall assist the Controller in investigating, mitigating
and remediating the breach.

---

## 9. Retention and deletion

9.1 Personal data is not retained longer than necessary for the purpose.

| Data type | Retention | Mechanism |
|---|---|---|
| Active family/child records | Until `DATA_RETENTION_DAYS` ({{value}}, default 1095 days) of inactivity | `anonymize_expired_data` scrubs PII in place |
| Audit logs | `AUDIT_LOG_RETENTION_DAYS` ({{value}}, default 1095 days) | Optional `--include-audit-logs` pruning |
| Checked-in children | Never auto-anonymised while actively checked in | Safeguarding — always resolvable during an event |

9.2 The Controller is responsible for confirming these defaults meet its own
retention policy and adjusting the environment variables accordingly.

---

## 10. Deletion and return on termination

10.1 Within {{30}} days of termination, the Processor shall, at the
Controller's choice: (a) securely delete all personal data including backups
and confirm in writing, or (b) return the data in a commonly readable format
(the existing export endpoint produces JSON/CSV), after which all copies are
deleted.

10.2 This obligation does not apply to data the Processor is required to
retain by law or order of a public authority.

---

## 11. Audit rights

11.1 The Controller may, on {{30}} days' written notice, audit or have a
mandated auditor audit the Processor's processing under this Agreement,
including inspection of relevant technical systems and documentation.

11.2 Audits are limited to once per twelve-month period unless a confirmed
incident justifies more, conducted so as to minimise disruption to the
Processor's operations, at the Controller's cost.

---

## 12. Governing law and disputes

12.1 This Agreement is governed by {{Swedish law}}.

12.2 Disputes are settled by negotiation in the first instance; failing that,
by {{the courts of ... / arbitration}}.

---

## 13. Miscellaneous

13.1 This Agreement, together with any technical annex provided under §6.3,
is the parties' entire agreement on the Processor's processing of personal
data and supersedes prior understandings on the subject.

13.2 Amendments must be in writing and signed by both parties.

13.3 If any provision is held invalid, the remaining provisions stay in force.

---

## Signatures

**Controller**

Name: _________________________ Organisation: {{CONTROLLER_NAME}}

Date: _________________________ Signature: _________________________

**Processor**

Name: _________________________ Organisation: {{PROCESSOR_NAME}}

Date: _________________________ Signature: _________________________

---

## Open questions and flags for legal review

1. **Contracting entity:** confirm whether {{sole trader / limited company}}
   is an appropriate Processor party for this Agreement — see the questions
   already sent to counsel in `docs/legal-request-to-law-firm.md`.
2. **Notice periods and audit cadence (§5.2, §10.1, §11.2):** confirm the
   placeholder day counts are reasonable for your jurisdiction and risk
   appetite.
3. **Sub-processor table (§5.1):** keep current — this is the first thing
   IMY asks for in an audit.
4. **Retention values (§9):** confirm `DATA_RETENTION_DAYS` /
   `AUDIT_LOG_RETENTION_DAYS` reflect a documented decision, not just the
   code defaults.
5. **Art. 9 condition:** confirmed in the DPIA (§2) and LIA — reference the
   same condition here for consistency across documents.
