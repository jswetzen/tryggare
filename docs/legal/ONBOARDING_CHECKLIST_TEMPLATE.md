# Congregation Onboarding Checklist — Template

*Turns the scattered guidance in `README.md` and the individual templates
into one operational checklist. Complete this before go-live for any new
organisation using Tryggare — whether self-hosted or on a hosted/managed
offering. Not legal advice; have the filled result reviewed by someone
qualified before relying on it.*

## 1. Legal documents

- [ ] **Read `README.md`** for what each template is and how the pieces fit
      together.
- [ ] **Legitimate Interest Assessment** — adopt
      `LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md` as your own, replacing
      every `{{PLACEHOLDER}}`. Do not ship it with a pre-filled conclusion —
      the balancing test is for *your* organisation to complete.
- [ ] **DPIA** — adopt `DPIA_TEMPLATE.md` as your own. This processing
      (children + Art. 9 health data) requires a DPIA; this isn't optional.
- [ ] **Privacy policy** — fill in `PRIVACY_POLICY_TEMPLATE.md` and publish it
      at a stable URL (see §2, `PRIVACY_POLICY_URL`).
- [ ] **Terms of Service** — fill in `TERMS_OF_SERVICE_TEMPLATE.md` for your
      staff/volunteers.
- [ ] **If hosted by someone else (not self-hosting):** get a signed
      Art. 28 DPA from the operator (`DPA_TEMPLATE.md` is what that should be
      based on) plus its `TECHNICAL_ANNEX.md` counterpart. Confirm the DPA's
      term is coterminous with your commercial agreement with the operator —
      an independently-terminable DPA can create the state "service
      continues, DPA terminated."
- [ ] **Breach process** — read `BREACH_NOTIFICATION_PROCESS.md` and confirm
      who on your side gets contacted and by when.
- [ ] **Consent form/wording** — confirm the health-consent notice text
      guardians see at registration (`checkin.healthConsentNotice` in the
      app's `en.json`/`sv.json`) matches what your LIA/privacy policy
      describes, in both languages if you serve both.

## 2. Technical configuration

Set these environment variables to match the policy you just published —
the defaults are placeholders, not a decision:

- [ ] `DATA_CONTROLLER_NAME`, `DATA_CONTROLLER_CONTACT_EMAIL`,
      `DATA_CONTROLLER_URL` — who guardians should contact.
- [ ] `PRIVACY_POLICY_URL` — where your filled `PRIVACY_POLICY_TEMPLATE.md`
      is actually published. The app's `/privacy` page links here.
- [ ] `DATA_RETENTION_DAYS` / `AUDIT_LOG_RETENTION_DAYS` — confirm the
      defaults (1095 days / 3 years each) reflect a decision you actually
      made, not just "whatever the code shipped with."
- [ ] `HEALTH_CONSENT_NOTICE_VERSION` — bump this whenever the consent
      notice wording changes; existing consent records keep the version they
      were actually granted under.
- [ ] Confirm the retention job is actually running: it's an in-app
      scheduler (daily, 03:00), not a cron entry you need to configure — but
      verify at least one scheduled run has completed after go-live.

## 3. Staff readiness

- [ ] Every staff member/volunteer has their own individual account — no
      shared logins (this is what the DPA's data-subject list and audit log
      both assume).
- [ ] Staff have read and acknowledged the Terms of Service (§1).
- [ ] Staff know the health-consent capture flow: the notice must actually be
      read aloud or shown on-screen before ticking consent, and declining
      must never block a child's registration or attendance.
- [ ] Staff know how to run a data-subject access/erasure request (DSAR):
      `FamilyViewSet` export/erase actions and the equivalent Django Admin
      actions, and what "erased" actually means (hard delete — see the DSAR
      section of `README.md`/`DPA_NOTE.md`).

## 4. Recommended, not yet mandatory to start

- [ ] **Art. 30 record of processing (ROPA)** — no template ships for this
      yet; still worth drafting your own before an audit, not during one.
- [ ] **Child-friendly notice** — a short, plain "what we know about you and
      why" aimed at children themselves (Art. 12 age-appropriate
      transparency).
- [ ] **DPO assessment note** — one paragraph documenting why a Data
      Protection Officer isn't required under Art. 37 (small scale, not a
      "large scale" core activity) — pre-empts the question rather than
      leaving it open.
- [ ] **If hosted:** confirm the operator has actually tested a backup
      restore. An untested backup is not a control.

## 5. Sign-off

**Completed by:** {{NAME / ROLE}}
**Date:** {{DATE}}
**Reviewed by (legal/DPO, if applicable):** {{NAME}}
