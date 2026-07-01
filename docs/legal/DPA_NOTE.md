# Data Processing Notes

*Template / guidance — adapt to your deployment. Last updated: {{DATE}}.*

This note covers the processor relationships that can arise when running
Tryggare. Which apply depends on how you deploy it.

## 1. Self-hosted (default)

If you run Tryggare on your own infrastructure and no third party operates it on
your behalf, you are the **sole controller** and no Data Processing Agreement
(DPA) with a Tryggare operator is required. You remain responsible for the
hosting environment (server, database, backups) and any infrastructure providers
you use — those providers may be your processors and may need their own DPAs.

## 2. Hosted / SaaS use

If you use a hosted version operated by a third party (or you operate a hosted
version for other organisations), that operator is a **processor** acting on the
controller's instructions. In that case you need:

- A **DPA** between controller and operator covering Art. 28 GDPR requirements
  (subject matter, duration, nature/purpose, data types, controller
  instructions, confidentiality, security, sub-processors, deletion/return,
  audit). See [`DPA_TEMPLATE.md`](DPA_TEMPLATE.md) for a signable draft.
- A **sub-processor list** (e.g. cloud hosting, managed database, email/SMS
  providers) with a process for notifying controllers of changes.
- Defined security measures and a breach-notification commitment (see
  `BREACH_NOTIFICATION_PROCESS.md`).

## 3. Import integrations

Tryggare can import family/registration data from external systems (see the
`imports/` app), e.g. **FestivalPro** and **Planning Center**. When you import:

- The source system is a separate controller/processor; confirm you have a lawful
  basis and the right to transfer that data into Tryggare.
- Store any API credentials securely (environment/secret storage, not in code).
- Record what is imported and when (the import history) as part of your
  accountability documentation.
- Apply the same retention/anonymisation to imported records as to any other.

Document the specific integrations you use, the data fields transferred, and the
controller/processor roles for each.
