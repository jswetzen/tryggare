# Legal & compliance templates

Tryggare is self-hosted: **each organisation that runs it is the data
controller** for the children's data it holds, and is responsible for its own
GDPR compliance. These files are **templates** to help you get there quickly —
they are not legal advice. Replace every `{{PLACEHOLDER}}` and have the result
reviewed by someone qualified before relying on it.

| File | Purpose |
|------|---------|
| [`PRIVACY_POLICY_TEMPLATE.md`](PRIVACY_POLICY_TEMPLATE.md) | Privacy notice to publish for parents/guardians. |
| [`TERMS_OF_SERVICE_TEMPLATE.md`](TERMS_OF_SERVICE_TEMPLATE.md) | Terms for staff/operators using the system. |
| [`LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md`](LEGITIMATE_INTEREST_ASSESSMENT_TEMPLATE.md) | LIA documenting your lawful basis. |
| [`DPIA_TEMPLATE.md`](DPIA_TEMPLATE.md) | Data Protection Impact Assessment — required for this kind of processing under Art. 35. |
| [`DPA_NOTE.md`](DPA_NOTE.md) | Processor/sub-processor notes for hosted use and the import integrations. |
| [`DPA_TEMPLATE.md`](DPA_TEMPLATE.md) | Signable Art. 28 DPA draft for the hosted/SaaS scenario. |
| [`BREACH_NOTIFICATION_PROCESS.md`](BREACH_NOTIFICATION_PROCESS.md) | What to do if data is breached. |

## How these connect to the running system

The app surfaces operator-configured controller details via environment
variables (see `backend/config/settings/base.py`):

- `DATA_CONTROLLER_NAME`, `DATA_CONTROLLER_CONTACT_EMAIL`, `DATA_CONTROLLER_URL`
- `PRIVACY_POLICY_URL` — link to your published full policy
- `DATA_RETENTION_DAYS` — drives the retention statement shown on `/privacy`

The public `/privacy` page reads these, and the public QR page links to it. Fill
the env vars in to match the policy you publish from these templates.
