# PRD: Automated Label Printing

**Feature area:** Printing  
**Status:** Ready for implementation  
**Depends on:** Existing check-in and print queue flows  
**Scope:** Backend (Django + Channels), Printer client (Python), Frontend (Svelte)

---

## 1. Overview

The system currently supports manual label printing: a staff member opens the print queue page, clicks Print for each child, and the browser opens a print-formatted page they send to any locally connected printer.

This feature adds automated label printing via dedicated Brother QL label printers. A lightweight Python client runs on a machine with a USB- or WiFi-connected Brother printer, authenticates with the backend using staff credentials, and receives print jobs over WebSocket. Staff can opt into auto-print at check-in, and can also trigger remote printing from the print queue page.

The feature is additive — manual printing continues to work unchanged.

---

## 2. Goals

- Remove the manual print step for high-throughput check-in scenarios.
- Support multiple named printers, selectable per check-in station.
- Degrade gracefully — if no printer is online, staff fall back to the existing manual flow.
- Keep the printer client simple and self-contained; no additional infrastructure required.

---

## 3. Concepts & Terminology

| Term | Definition |
|---|---|
| **Printer client** | Python process running on a LAN machine with a Brother printer attached. Authenticates as a staff user and maintains a persistent WebSocket connection. |
| **Printer record** | Django model representing a registered printer. Stores UUID, display name, online status, and last-seen timestamp. |
| **Print job** | A record representing a request to print a specific check-in label. Holds a reference to the check-in, the target printer, status, and timestamps. |
| **Unassigned job** | A print job with no printer assigned — created when auto-print is enabled but no printer is selected, or when the assigned printer goes offline. |
| **Manual print** | Existing flow: browser opens `/print/<checkin_id>/`, staff prints via the browser. |
| **Auto-print** | New flow: a PrintJob is created and pushed over WebSocket to the target printer client, which fetches the job label URL and renders it via Playwright. |

---

## 4. User Stories

### Check-in staff
- As a check-in staff member, I can select which printer to use for this station, and my choice is remembered for the rest of my session on this device.
- As a check-in staff member, I can enable auto-print so that a label is sent to the selected printer automatically when a child checks in.
- As a check-in staff member, if no printer is available I am not blocked — I can still check in the child and print manually.

### Print queue staff
- As a print queue operator, each queued row shows a single contextual action button: "Assign printer" if the job is unassigned, or the assigned printer's name with an option to resend if already assigned.
- As a print queue operator, I can still use the existing manual Print button regardless of printer availability.

### Printer operator
- As a printer operator, I can run the printer client on a LAN machine and have it register with the backend using a staff account.
- As a printer operator, the client reconnects automatically if the connection drops, with exponential backoff.

---

## 5. Backend Design

### 5.1 New models

**`Printer`**

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField (PK) | Set by the client on first registration. |
| `name` | CharField | Human-readable display name, e.g. "Foyer Printer". |
| `is_online` | BooleanField | True while the client's WS connection is active (post grace period). |
| `last_seen_at` | DateTimeField | Updated on every WS heartbeat or inbound message. |
| `created_at` | DateTimeField | Auto. |

**`PrintJob`**

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField (PK) | Auto-generated. Also serves as the unguessable URL token for the label page. |
| `checkin` | ForeignKey → CheckIn | The check-in record this label is for. |
| `printer` | ForeignKey → Printer (nullable) | Null = unassigned. |
| `status` | CharField (enum) | `pending` / `sent` / `completed` / `failed` |
| `created_at` | DateTimeField | Auto. |
| `sent_at` | DateTimeField (nullable) | Set when job is pushed to the printer client over WS. |
| `completed_at` | DateTimeField (nullable) | Set when client ACKs completion. |

**Status transitions:**
- `pending → sent`: backend pushes job over WebSocket to the printer client.
- `sent → completed`: printer client sends a completion ACK.
- `sent → failed`: printer client sends a failure message, or no ACK within 10 seconds.
- `pending or sent → pending (unassigned)`: assigned printer goes offline; job is moved to the unassigned pool.

### 5.2 Printer lifecycle

**Registration:** on WS connect, the printer client sends a `printer_register` message containing its UUID and name. The backend upserts the Printer record and marks it online.

**Online detection:** `is_online` is set to true immediately on registration. `last_seen_at` is updated on every inbound message including heartbeats.

**Offline detection:** implemented entirely within the Django Channels async consumer — no Celery or external scheduler required. On WS disconnect, the consumer schedules an `asyncio` coroutine that sleeps 30 seconds then marks the printer offline and reassigns its jobs. If the client reconnects within those 30 seconds, the pending coroutine is cancelled. A process restart drops all WS connections, causing clients to reconnect immediately, so no jobs are orphaned in practice.

**Job reassignment on offline:** when a Printer is marked offline, all PrintJobs in `pending` or `sent` status assigned to it are moved to unassigned (`printer = null`, `status = pending`), making them available for manual printing or reassignment.

**Re-registration:** if a client reconnects with the same UUID, the existing record is updated — name may change, `is_online` is set back to true, and any pending offline coroutine is cancelled.

### 5.3 WebSocket messages

The printer client authenticates by POSTing to the existing login endpoint with username and password, receiving a session cookie. It then opens a WebSocket connection carrying that cookie — Django Channels authenticates it via standard session middleware, identical to browser clients. No new auth mechanism is required.

WebSocket message types are added alongside existing types. All clients receive all messages and ignore types they don't handle — no group separation is introduced at this stage.

| Direction | Type | Payload |
|---|---|---|
| Client → Server | `printer_register` | `{ uuid, name }` |
| Client → Server | `printer_heartbeat` | `{ uuid }` |
| Client → Server | `print_job_completed` | `{ job_id }` |
| Client → Server | `print_job_failed` | `{ job_id, reason }` |
| Server → Client | `print_job` | `{ job_id, label_url }` |
| Server → Client | `printer_registered` | `{ uuid, name }` — confirmation |
| Server → Client | `printer_status_changed` | `{ uuid, name, is_online }` — broadcast to all clients |

`label_url` is the full absolute URL of the unauthenticated label endpoint (see §5.4). The printer client fetches this URL directly with no auth headers.

### 5.4 New endpoints

**`GET /api/printing/printers/`**  
Returns all printers with `id`, `name`, `is_online`. Used by the UI to populate the printer selector.

**`POST /api/printing/jobs/`**  
Creates a PrintJob. Accepts `{ checkin_id, printer_id (optional) }`. If `printer_id` is provided and the printer is online, the job is immediately pushed over WS.

**`POST /api/printing/jobs/<id>/assign/`**  
Assigns or re-assigns a job to a printer. Triggers a WS push if the printer is online.

**`GET /print-job/<job_uuid>/label/`**  
Unauthenticated. Returns the label HTML page for the given print job, identical in layout to the existing `/print/<checkin_id>/` page but with `?no-autoprint` behaviour built in (no `setTimeout(window.print())` call). Responds with 404 if the job does not exist or is no longer in `pending` or `sent` status.

The `PrintJob` UUID (UUID4) is unguessable and acts as a bearer token scoped to a single job while it is active. The WS connection over which the UUID is transmitted must use TLS in production.

---

## 6. Printer Client

### 6.1 Overview

A standalone Python script/package configured via environment variables or a config file. It is intended to run as a long-lived process, e.g. via systemd or a shell loop.

### 6.2 Responsibilities

1. POST to the login endpoint with staff credentials → receive session cookie.
2. Open a WebSocket connection with the session cookie and send `printer_register`.
3. Send `printer_heartbeat` every 10 seconds.
4. On receipt of `print_job`: fetch `label_url`, render via Playwright, print via `brother_ql`, send ACK.
5. On print failure: send `print_job_failed` with a reason string.
6. On WS disconnect: reconnect with exponential backoff.

### 6.3 Rendering

The client uses **Playwright** (headless Chromium) to render the label page:

1. Navigate to `label_url` (no auth required).
2. Wait for the QR code image to finish loading.
3. Screenshot the `.label` div at the correct DPI for the configured label size (e.g. 615×341px for 52×29mm at 300dpi).
4. Save as PNG, pass to `brother_ql` for raster conversion and printing.

This approach ensures the HTML label template remains the single source of truth for layout, used identically by manual browser printing and automated printing.

### 6.4 Configuration

| Key | Description |
|---|---|
| `BACKEND_URL` | Base URL of the Django backend, e.g. `https://checkin.example.com` or `http://192.168.1.10:8000`. |
| `STAFF_USERNAME` / `STAFF_PASSWORD` | Credentials for a staff account. |
| `PRINTER_UUID` | Stable UUID4 for this printer instance. Generate once and persist. |
| `PRINTER_NAME` | Display name shown in the UI, e.g. "Foyer Printer". |
| `PRINTER_IDENTIFIER` | USB or network address for the Brother printer, e.g. `usb://0x04f9:0x209d`. |
| `PRINTER_BACKEND` | `brother_ql` backend identifier: `pyusb` or `network`. |
| `PRINTER_MODEL` | Brother model string, e.g. `QL-810W`. |
| `LABEL_SIZE` | Label dimensions string, e.g. `52x29`. |

---

## 7. Frontend Changes

### 7.1 Check-in UI

A **printer selector** is added to the check-in page. It lists all printers from `GET /api/printing/printers/` with online/offline status indicated. The selected printer UUID is persisted in `localStorage` so the choice survives page reloads on that device.

An **auto-print toggle** is also added. When enabled, completing a check-in creates a PrintJob via `POST /api/printing/jobs/` targeting the selected printer. If auto-print is on but no printer is selected, the job is created unassigned.

If no printers are registered, both the selector and toggle are hidden — no UI noise for setups that don't use automated printing.

### 7.2 Print queue page

The actions column gains a **single contextual button** alongside the existing manual Print button:

- **"Assign printer"** — shown when the job is unassigned. Clicking opens a popover to select an online printer, then calls `POST /api/printing/jobs/` or `POST /api/printing/jobs/<id>/assign/`.
- **"Sent to [name]" / "Resend"** — shown when a printer is already assigned. Allows re-triggering the WS push.

On success, the row updates optimistically to reflect the new assignment.

The existing Print button (manual browser print) is unchanged and always visible.

Printer online/offline status in the selector is kept current via the `printer_status_changed` WebSocket broadcast — no page refresh required.

---

## 8. Out of Scope

- Printer management UI (rename, delete). Printers are managed by running or stopping the client process.
- Per-event or per-session printer assignment. Selection is per device via `localStorage`.
- Label template configuration. The existing print page layout is used as-is.
- Print history or audit log beyond what `PrintJob` records capture.
- Support for non-Brother printers.

---

## 9. Implementation Order

1. **Backend models & API** — `Printer` and `PrintJob` models, migrations, REST endpoints.
2. **WebSocket consumer** — printer registration, heartbeat handling, job push, ACK handling, asyncio-based offline detection and job reassignment.
3. **Label endpoint** — unauthenticated `/print-job/<job_uuid>/label/` with `no-autoprint` behaviour.
4. **Printer client** — auth, WS connection, heartbeat, job receipt, Playwright render, `brother_ql` print, ACK.
5. **Frontend (check-in)** — printer selector, auto-print toggle, `localStorage` persistence.
6. **Frontend (print queue)** — contextual assign/resend button, WS-driven status updates.
