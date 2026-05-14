#!/usr/bin/env python3
"""
Printer client for the Conference Child Management System.

Connects to the backend WebSocket, receives print jobs, renders labels
with WeasyPrint + pymupdf, and sends to a Brother QL printer.

Configuration via environment variables (see .env.example).
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid

import fitz  # pymupdf
import requests
import websockets
from dotenv import load_dotenv
from weasyprint import HTML

# Load .env file if present
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "admin")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "admin123")

PRINTER_UUID = os.environ.get("PRINTER_UUID", str(uuid.uuid4()))
PRINTER_NAME = os.environ.get("PRINTER_NAME", "Label Printer")
PRINTER_IDENTIFIER = os.environ.get("PRINTER_IDENTIFIER", "")  # e.g. usb://0x04f9:0x209c
PRINTER_BACKEND = os.environ.get("PRINTER_BACKEND", "pyusb")   # pyusb | network | linux_kernel
PRINTER_MODEL = os.environ.get("PRINTER_MODEL", "QL-810W")
LABEL_SIZE = os.environ.get("LABEL_SIZE", "29x90")  # die-cut: 29x90, 62x100 | endless: 29, 62

# Dry-run: skip actual printing (useful for testing)
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

# Label screenshot DPI - higher = better print quality
SCREENSHOT_DPI = int(os.environ.get("SCREENSHOT_DPI", "300"))

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("printer-client")


# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────

def authenticate() -> requests.Session:
    """Authenticate with the backend and return a session with cookies."""
    session = requests.Session()

    # Get CSRF token
    resp = session.get(f"{BACKEND_URL}/api/csrf/")
    resp.raise_for_status()
    csrf_token = resp.json().get("csrfToken") or resp.cookies.get("csrftoken")

    if not csrf_token:
        # Try cookie
        csrf_token = session.cookies.get("csrftoken")

    # Login
    resp = session.post(
        f"{BACKEND_URL}/api/auth/login/",
        json={"username": STAFF_USERNAME, "password": STAFF_PASSWORD},
        headers={"X-CSRFToken": csrf_token, "Referer": BACKEND_URL},
    )
    resp.raise_for_status()
    log.info("Authenticated as %s", STAFF_USERNAME)
    return session


def get_ws_url(http_session: requests.Session) -> str:
    """Build WebSocket URL from BACKEND_URL, replacing http(s) with ws(s)."""
    base = BACKEND_URL.rstrip("/")
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://"):]
    else:
        ws_base = "ws://" + base
    return f"{ws_base}/ws/checkins/"


def build_ws_headers(http_session: requests.Session) -> dict:
    """Extract session cookie for WebSocket authentication."""
    cookies = "; ".join(f"{k}={v}" for k, v in http_session.cookies.items())
    return {"Cookie": cookies}


# ─────────────────────────────────────────────────────────────────────────────
# Label rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_label(label_url: str) -> bytes:
    """
    Fetch the label page and render it to PNG using WeasyPrint + pymupdf.
    Returns PNG bytes.
    """
    sep = "&" if "?" in label_url else "?"
    url = f"{label_url}{sep}label={LABEL_SIZE}"

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    pdf_bytes = HTML(string=resp.text, base_url=url).write_pdf()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = doc[0].get_pixmap(
        matrix=fitz.Matrix(SCREENSHOT_DPI / 72, SCREENSHOT_DPI / 72),
        alpha=False,
    )
    return pix.tobytes("png")


# ─────────────────────────────────────────────────────────────────────────────
# Printing
# ─────────────────────────────────────────────────────────────────────────────

def get_label_target_size() -> tuple[int, int]:
    """
    Return the expected (width, height) in pixels for the rendered label
    based on LABEL_SIZE. Landscape orientation (length x width).
    brother_ql's rotate="90" rotates it to portrait for printing.
    """
    try:
        from brother_ql.labels import ALL_LABELS
        for label in ALL_LABELS:
            if label.identifier == LABEL_SIZE:
                # dots_printable is (width, length) in portrait
                # We render landscape: (length, width)
                return (label.dots_printable[1], label.dots_printable[0])
    except ImportError:
        pass
    # Fallback for common sizes
    KNOWN_SIZES = {
        "29x90": (991, 306),
        "62x100": (1164, 618),
        "29x42": (425, 306),
    }
    return KNOWN_SIZES.get(LABEL_SIZE, (991, 306))


def print_label(png_bytes: bytes) -> None:
    """
    Send PNG bytes to the Brother QL printer via brother_ql.
    Skipped in DRY_RUN mode.
    """
    if DRY_RUN:
        log.info("[DRY RUN] Would print %d bytes of PNG data", len(png_bytes))
        return

    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
        from PIL import Image
        import io

        if not hasattr(Image, "ANTIALIAS"):
            Image.ANTIALIAS = Image.LANCZOS

        image = Image.open(io.BytesIO(png_bytes))
        target_w, target_h = get_label_target_size()

        log.info("Screenshot %dx%d, target %dx%d (landscape)",
                 image.size[0], image.size[1], target_w, target_h)

        if image.size != (target_w, target_h):
            image = image.resize((target_w, target_h), Image.LANCZOS)

        qlr = BrotherQLRaster(PRINTER_MODEL)
        qlr.exception_on_warning = True

        instructions = convert(
            qlr=qlr,
            images=[image],
            label=LABEL_SIZE,
            rotate="90",
            threshold=70.0,
            dither=False,
            compress=False,
            red=False,
            dpi_600=False,
            hq=True,
            cut=False,
        )

        send(
            instructions=instructions,
            printer_identifier=PRINTER_IDENTIFIER,
            backend_identifier=PRINTER_BACKEND,
            blocking=True,
        )
        log.info("Label printed successfully")
    except Exception as exc:
        log.error("Printing failed: %s", exc)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Main WebSocket loop
# ─────────────────────────────────────────────────────────────────────────────

async def run_client(http_session: requests.Session) -> None:
    """Open WS, register printer, handle jobs. Raises on disconnect."""
    ws_url = get_ws_url(http_session)
    headers = build_ws_headers(http_session)

    log.info("Connecting to %s", ws_url)
    async with websockets.connect(ws_url, additional_headers=headers, origin=BACKEND_URL.rstrip("/")) as ws:
        log.info("Connected")

        # Register printer
        await ws.send(json.dumps({
            "type": "printer_register",
            "uuid": PRINTER_UUID,
            "name": PRINTER_NAME,
        }))
        log.info("Registered as printer '%s' (UUID: %s)", PRINTER_NAME, PRINTER_UUID)

        # Start heartbeat task
        heartbeat_task = asyncio.ensure_future(heartbeat_loop(ws))

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "print_job":
                    data = msg.get("data", {})
                    job_id = data.get("job_id")
                    printer_id = data.get("printer_id")
                    label_url = data.get("label_url")

                    # Only handle jobs assigned to this printer
                    if printer_id != PRINTER_UUID:
                        continue

                    log.info("Received print job %s, label_url=%s", job_id, label_url)
                    asyncio.ensure_future(handle_print_job(ws, job_id, label_url))
        finally:
            heartbeat_task.cancel()


async def heartbeat_loop(ws) -> None:
    """Send heartbeat every 10 seconds."""
    while True:
        await asyncio.sleep(10)
        try:
            await ws.send(json.dumps({
                "type": "printer_heartbeat",
                "uuid": PRINTER_UUID,
            }))
        except Exception:
            break


async def handle_print_job(ws, job_id: str, label_url: str) -> None:
    """Render and print a single label, then report result via WS."""
    try:
        log.info("Rendering label for job %s", job_id)
        png_bytes = render_label(label_url)

        log.info("Printing label for job %s", job_id)
        print_label(png_bytes)

        await ws.send(json.dumps({
            "type": "print_job_completed",
            "job_id": job_id,
        }))
        log.info("Job %s completed", job_id)
    except Exception as exc:
        log.error("Job %s failed: %s", job_id, exc)
        try:
            await ws.send(json.dumps({
                "type": "print_job_failed",
                "job_id": job_id,
                "reason": str(exc),
            }))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Startup checks
# ─────────────────────────────────────────────────────────────────────────────

def check_ipp_usb() -> None:
    """Warn if ipp-usb service is active — it causes USB reset loops."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "ipp-usb.service"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip() == "active":
            log.warning("=" * 60)
            log.warning("ipp-usb.service is ACTIVE — this causes USB reset loops!")
            log.warning("Run: sudo systemctl stop ipp-usb.service")
            log.warning("=" * 60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # systemctl not available (e.g. macOS/Windows)


def discover_and_check_printer() -> str:
    """
    Auto-discover printer if PRINTER_IDENTIFIER is empty.
    Query printer status and log model/label info.
    Returns the printer identifier to use.
    """
    global PRINTER_IDENTIFIER

    if PRINTER_BACKEND == "network":
        if not PRINTER_IDENTIFIER:
            log.error("PRINTER_IDENTIFIER is required for network backend (e.g. tcp://192.168.1.50)")
            sys.exit(1)
        log.info("Network backend: %s", PRINTER_IDENTIFIER)
        try:
            from brother_ql.backends.helpers import get_network_status
            status_info = get_network_status(PRINTER_IDENTIFIER)
            if status_info:
                log.info("Printer status via SNMP: %s", status_info)
            else:
                log.warning("Could not query printer status via SNMP (puresnmp not installed?)")
        except Exception as exc:
            log.warning("Could not query printer status: %s", exc)
        return PRINTER_IDENTIFIER

    try:
        from brother_ql.backends.helpers import discover
        printers = discover(PRINTER_BACKEND)
    except Exception as exc:
        log.warning("Printer discovery failed: %s", exc)
        if not PRINTER_IDENTIFIER:
            log.error("No PRINTER_IDENTIFIER set and discovery failed")
            sys.exit(1)
        return PRINTER_IDENTIFIER

    if not PRINTER_IDENTIFIER:
        if len(printers) == 1:
            PRINTER_IDENTIFIER = printers[0]["identifier"]
            log.info("Auto-discovered printer: %s", PRINTER_IDENTIFIER)
        elif len(printers) == 0:
            log.error("No printers found via %s backend. Is the printer connected?", PRINTER_BACKEND)
            sys.exit(1)
        else:
            identifiers = [p["identifier"] for p in printers]
            log.error("Multiple printers found — set PRINTER_IDENTIFIER: %s", identifiers)
            sys.exit(1)
    else:
        log.info("Using configured printer: %s", PRINTER_IDENTIFIER)

    # Query printer status
    try:
        from brother_ql.backends.helpers import get_printer, get_status
        printer = get_printer(PRINTER_IDENTIFIER, PRINTER_BACKEND)
        status_info = get_status(printer)
        log.info("Printer status: %s", status_info)
        printer.dispose()
    except Exception as exc:
        log.warning("Could not query printer status: %s", exc)

    return PRINTER_IDENTIFIER


# ─────────────────────────────────────────────────────────────────────────────
# Entry point with reconnect logic
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    log.info("Printer client starting — model=%s, label=%s, backend=%s",
             PRINTER_MODEL, LABEL_SIZE, PRINTER_BACKEND)

    check_ipp_usb()
    discover_and_check_printer()

    log.info("Printer: %s via %s", PRINTER_IDENTIFIER, PRINTER_BACKEND)
    if DRY_RUN:
        log.info("DRY RUN mode — printing will be skipped")

    backoff = 1
    http_session = None

    while True:
        try:
            if http_session is None:
                http_session = authenticate()
            await run_client(http_session)
            # If we reach here without exception, WS closed cleanly
            backoff = 1
        except (websockets.ConnectionClosed,
                websockets.WebSocketException) as exc:
            log.warning("WebSocket disconnected: %s — reconnecting in %ds", exc, backoff)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (401, 403):
                log.warning("Session expired, re-authenticating")
                http_session = None
            else:
                log.error("HTTP error: %s — reconnecting in %ds", exc, backoff)
        except Exception as exc:
            log.error("Unexpected error: %s — reconnecting in %ds", exc, backoff)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
