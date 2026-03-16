# Printer Client Improvements

## Context

The printer client (`printer-client/client.py`) uses brother_ql + Playwright to render and print labels.
Current state is functional but has several rough edges that need addressing before it's production-ready.

---

## 1. Dynamic label sizing (don't hardcode page size)

**Problem:** The label template is rendered at a fixed size (currently wrong — portrait vs landscape mismatch).
The client hacks around it with `image.rotate(90).resize(...)`. This is lossy.

**Better approach:** Let the printer client query the printer for its label size, then pass that size
to the label render endpoint (or derive CSS dimensions server-side) so the page renders at exactly
the right pixel dimensions for that label. The server should render to whatever size the printer requests.

**Details:**
- `brother_ql.reader.BrotherQLReader` / status commands can return the installed label size
- Endpoint could accept `?label=29x90` or similar and set correct CSS dimensions
- Remove the rotate/resize workaround from `client.py` once the page renders correctly
- The `.label` CSS element at `device_scale_factor = 300/96 ≈ 3.125` needs:
  - 29×90mm die-cut: CSS 98×317px → device 306×991px (portrait)
- See old notes: `print_page_problems.md` (now superseded by this task)

---

## 2. USB support on Mac and Windows

**Problem:** USB is the most common connection scenario (WiFi not always available at events).
USB permissions are a hassle on Linux. On Mac/Windows it's different.

**Tasks:**
- Test and document USB printer setup on macOS (likely needs no special permissions)
- Test and document USB printer setup on Windows
- brother_ql USB device path on Mac: usually `/dev/usb/lp0` equivalent or `usb://...`
- The `brother_ql` package uses `usb` library on Linux, `pyusb` elsewhere — document what's needed

---

## 3. Auto-detect printer via USB (don't require config)

**Problem:** Requiring the user to set `PRINTER_IDENTIFIER` in `.env` is friction.
If only one Brother printer is connected via USB, we should find it automatically.

**Implementation sketch:**
```python
from brother_ql.backends.helpers import discover
printers = discover('pyusb')  # or 'linux_kernel' on Linux
# pick the first one, or error if none/multiple
```

**Also:** Use the discovered printer's model and label size to:
- Validate against any configured `PRINTER_MODEL` (fail loudly if mismatch)
- Set render dimensions dynamically (see item 1)

---

## 4. Status check on startup

On startup (before registering with the server), the client should:
1. Query the printer status (model, label size, paper feed status)
2. Log this info prominently
3. If configured values conflict with discovered values → fail with a clear error message
4. Pass label size info to the server when registering (so the server can render correctly)

---

## Priority

Medium. The system works with WiFi + manual config. USB auto-detect and dynamic sizing
would make onboarding at a new event much smoother.
