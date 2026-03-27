# Deferred Tasks

Low-priority items to revisit after the core system is stable.
Each file is a lightweight stub — enough context to pick up the work later.

| File | Topic | Priority |
|------|-------|----------|
| `archive/printer_client_improvements.md` | ~~USB support, auto-detect, dynamic label sizing~~ **Done** (remaining: Mac/Windows USB docs) | Low |
| `qr_scan_checkin.md` | Scan ticket QR codes at check-in | Medium |
| `planning_center_import.md` | Import from Planning.Center (church use case) | Low |
| `festivalpro_import_verification.md` | Manual verification of FestivalPro import | Operational |
| `print_queue_stale_on_checkout.md` | Cancel pending print queue entries on checkout | Low |
| `open_source_launch.md` | Repo cleanup, governance docs, CI/CD, and marketing for public launch | Medium |

## Prototypes

Exploratory code lives in `../prototypes/` — not production code, just reference implementations.

| File | Notes |
|------|-------|
| `qr_prototype.js` | React component using html5-qrcode (reference for QR scan feature) |
