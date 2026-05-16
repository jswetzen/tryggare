# Printer Client Improvements

## Context

The printer client (`printer-client/client.py`) uses brother_ql + Playwright to render and print labels.

---

## 1. Dynamic label sizing (don't hardcode page size) — DONE

Template now accepts `?label=29x90` query parameter. Client passes label size to the URL.
Server renders at correct CSS dimensions. No more rotate/resize hack in client.py.

---

## 2. USB support on Mac and Windows

**Problem:** USB permissions differ across platforms.

**Tasks:**
- Test and document USB printer setup on macOS (likely needs no special permissions)
- Test and document USB printer setup on Windows
- Linux USB setup is now documented in `printer-client/README.md`

---

## 3. Auto-detect printer via USB (don't require config) — DONE

Client auto-discovers via `discover(PRINTER_BACKEND)` when `PRINTER_IDENTIFIER` is empty.
Picks the first printer if exactly one found, errors on zero or multiple.

---

## 4. Status check on startup — DONE

Client now:
1. Checks for ipp-usb service (warns if active)
2. Auto-discovers or validates configured printer
3. Queries printer status and logs model/label info
4. Logs configuration summary before connecting

---

## Remaining

- **Item 2**: Mac/Windows USB support (untested)
- **Upstream PR**: Submit POC patches (ESC@ init, timeout fixes) to jswetzen/brother_ql-inventree

## Priority

Low. Core functionality is stable. Mac/Windows testing when hardware is available.
