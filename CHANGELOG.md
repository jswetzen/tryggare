# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/) and is currently in alpha (pre-1.0).

---

## [Unreleased]

- QR scan overlay for check-in (bulk scan flow refinement)
- Undo checkout action

---

## [0.6.0] — 2026-03

### Added
- QR scan overlay for check-in: scan a ticket's QR code to look up a child directly
- SNMP-based printer status for Brother QL network backend (more reliable than USB polling)
- Label size auto-detection and dimension improvements
- Print completion feedback in printer client

### Changed
- Printer client: switched to SNMP status readback for network printers

---

## [0.5.0] — 2026-01

### Added
- Label printing integration: Brother QL printer support via `printer-client/`
- Print queue page: view pending/completed print jobs, assign printers
- WebSocket-driven auto-print: label prints automatically on check-in when a printer is selected
- Printer model with online/offline tracking and 30-second heartbeat timeout
- PrintJob model with status lifecycle (pending → assigned → completed/failed)
- 14 unit tests for Printer/PrintJob models

---

## [0.4.0] — 2025-12

### Added
- FestivalPro data import: parse and import family/child data from FestivalPro booking exports
- Planning Center import: fetch families and children via Planning Center API
- Import source management UI (admin only)
- Raw source data stored on import records for debugging

### Fixed
- FestivalPro parser: duplicate-key age field handling, various parsing edge cases

---

## [0.3.0] — 2025-11

### Added
- Full internationalization (i18n): Swedish and English throughout frontend and backend
- Language switcher in UI
- Localized error messages on login, import, and check-in flows
- Swedish set as default language
- Norwegian translation stubs (partial)

---

## [0.2.0] — 2025-11

### Added
- Event and Session models: children are checked in to specific sessions
- One-child-per-session enforcement (business rule)
- Ticket model linking children to sessions
- UUID QR tokens: each child gets a cryptographically secure token
- Public read-only QR page (`/qr/<token>/`) — no login required
- Real-time sync: WebSocket via Django Channels broadcasts check-in/out events to all open stations
- Valkey (Redis-compatible) channel layer for WebSocket broadcast
- Audit log: every check-in/out action attributed to a staff member with timestamp

---

## [0.1.0] — 2025-11

### Added
- Initial Django 5 + SvelteKit scaffold
- Family, Parent, and Child models with REST API
- Staff authentication (Django session-based)
- Check-in and check-out workflows with business logic enforcement
- Multi-station support: any logged-in staff member can check in/out from any browser
- Django admin interface for data management
- Docker Compose setup for development and production
- PostgreSQL 16 database
- Basic E2E test suite (Selenium)
