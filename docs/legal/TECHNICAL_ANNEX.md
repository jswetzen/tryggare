# Technical Annex — Infrastructure and Security Measures

*Template — confidential technical detail supporting §6 of
[`DPA_TEMPLATE.md`](DPA_TEMPLATE.md) and §4/§6 of
[`DPIA_TEMPLATE.md`](DPIA_TEMPLATE.md). Replace `{{PLACEHOLDER}}` values and
confirm every fact against the actual production deployment before sharing —
this describes {{one candidate hosting setup; confirm it matches the
environment Tryggare Moln customers are actually served from}}. Last updated:
{{DATE}}.*

## 1. Hosting

{{CONFIRM: this section assumes self-managed infrastructure (Proxmox VE,
homelab-style), consistent with the "no external cloud provider" statement in
`docs/legal-request-to-law-firm.md`. If Tryggare Moln customers are instead
hosted with a third-party provider (e.g. a Swedish VPS/cloud host), that
provider is a sub-processor and must be added to DPA_TEMPLATE.md §5 — do not
send this annex until the hosting model in this section matches reality.}}

- Compute: Proxmox VE cluster, primary node in Sweden ({{CITY}}). Each
  Tryggare Moln customer runs as an isolated container (LXC) — no
  multi-tenant database, consistent with the "one instance per church" data
  isolation described in the DPIA §4.
- Storage: ZFS-backed (raidz2), local to the hosting node.
- Reverse proxy / TLS: Traefik terminates TLS at the edge; certificates via
  Let's Encrypt, auto-renewed. HTTP requests are redirected to HTTPS.
- Network exposure: only the application's HTTP(S) port is internet-facing
  via the reverse proxy; the database and internal services are not directly
  reachable from the internet.

## 2. Backups

- Automated nightly backups (Proxmox Backup Server), running at 01:00.
- Backups are client-side encrypted (AES-256-GCM) before leaving the source
  host.
- Offsite copy: confirmed 2026-07-04 as in the backup chain for the Tryggare
  Moln production container specifically (not just other services) — nightly
  backups are replicated to a second, geographically separate private
  residence as part of the same automated job that backs up every container
  on the primary host. Both the primary and off-site locations are private
  residences with comparable physical security (locked premises, no public
  access). The off-site copy is protected independently of physical security
  at that location: it is encrypted before it ever leaves the primary site,
  and the decryption key exists only there — the off-site location cannot
  read the data it stores even in the event of a full compromise of that
  host.
- {{CONFIRM retention/rotation policy — as of this draft, backups are
  retained indefinitely with no automatic expiry configured; a fixed
  retention window has not yet been decided.}}

## 3. Encryption at rest

- ZFS native encryption (AES-256-GCM) with TPM-sealed auto-unlock has been
  validated on the primary hosting node.
- {{OPEN — CONFIRM BEFORE RELYING ON THIS: as of this draft, that encrypted
  dataset is a validated proof of concept, not confirmed as the storage
  location for the live Tryggare Moln database/container. Verify the actual
  Postgres data volume for production customer instances sits on an
  encrypted dataset before stating "encryption at rest" as a completed
  control in the DPA/DPIA. If it doesn't yet, this is the single largest gap
  between the current DPIA's stated mitigations and actual production
  state.}}

## 4. Monitoring and alerting

- Infrastructure health monitoring in place (disk/CPU/RAM, service uptime),
  with failure alerts routed to a push-notification channel.
- {{Application-level uptime/status page for customers — tracked as GTM gap
  #5, not yet built as of this draft.}}

## 5. Access control

- Administrative access to the hosting infrastructure is limited to
  {{list of individuals/roles with admin access}}.
- {{Describe SSH key management, any remote-access tunnel (e.g. WireGuard)
  used to reach management interfaces, and whether management interfaces are
  internet-exposed.}}

## 6. Sub-processors touching infrastructure

- {{List any third party with access to the physical/virtual infrastructure
  or its backups — e.g. datacenter/colo provider if the hardware isn't
  purely on residential/office premises, DNS provider, certificate
  authority (Let's Encrypt, informational only). Cross-check against
  DPA_TEMPLATE.md §5 so the two documents agree.}}
