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
- Storage: {{describe the actual storage backend — e.g. ZFS, LVM, local disk
  — local to the hosting node}}.
- Reverse proxy / TLS: Traefik terminates TLS at the edge; certificates via
  Let's Encrypt, auto-renewed. HTTP requests are redirected to HTTPS.
- Network exposure: only the application's HTTP(S) port is internet-facing
  via the reverse proxy; the database and internal services are not directly
  reachable from the internet.

## 2. Backups

- Automated nightly backups (Proxmox Backup Server), running at 01:00.
- Backups are client-side encrypted (AES-256-GCM) before leaving the source
  host.
- {{CONFIRM offsite copy: does a second, geographically separate backup copy
  exist, and is it actually in the chain for THIS customer's production
  container specifically (not just other services on shared
  infrastructure)? If so, describe the physical security of that second
  location, and confirm whether the backup remains encrypted there with a
  key that isn't available at that location — so a compromise of the
  offsite location alone doesn't expose the data. If both locations are
  private premises rather than commercial facilities, describe their
  security posture at a level of detail proportionate to what's actually
  needed (e.g. "private residence, comparable security to the primary
  site" rather than naming individuals or addresses).}}
- {{CONFIRM retention/rotation policy — describe how long backups are kept
  and whether that's a fixed, enforced window or indefinite retention.}}

## 3. Encryption at rest

- {{CONFIRM the actual encryption-at-rest mechanism protecting the
  database/container data volume for production customer instances — e.g.
  disk/volume-level encryption (LUKS/dm-crypt, BitLocker) or filesystem-native
  encryption (ZFS native encryption or similar), and how the decryption key
  is supplied at boot (manual entry, TPM-sealed auto-unlock, a
  key-management service, etc.).}}
- {{State the threat model plainly rather than overselling it: encryption
  at rest with the key material available on the same host typically
  defends against disk theft or decommissioning, NOT against a compromised
  host or container escape — root/admin access on that host still sees
  plaintext. Say this explicitly rather than implying encryption alone
  makes the host itself secure.}}
- {{Confirm scope: does this cover the full container/VM, or only a specific
  data volume (e.g. just the database's data directory)? If only partial,
  say so — application code, logs, and any secrets/environment files outside
  that volume may not be covered, and shouldn't be implied to be.}}
- {{CONFIRM this is validated in actual production for live customer
  instances, not just a proof of concept on a test volume — state plainly if
  it isn't yet, since that gap matters more than almost anything else in
  this document.}}

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
