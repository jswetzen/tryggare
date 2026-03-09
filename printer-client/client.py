#!/usr/bin/env python3
"""
Printer client for the Conference Child Management System.

Connects to the backend WebSocket, receives print jobs, renders labels
with Playwright (headless Chromium), and sends to a Brother QL printer.

Configuration via environment variables (see .env.example).
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import requests
import websockets
from dotenv import load_dotenv
from playwright.async_api import async_playwright

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
PRINTER_IDENTIFIER = os.environ.get("PRINTER_IDENTIFIER", "")  # e.g. usb://0x04f9:0x2042
PRINTER_BACKEND = os.environ.get("PRINTER_BACKEND", "pyusb")   # pyusb | network | linux_kernel
PRINTER_MODEL = os.environ.get("PRINTER_MODEL", "QL-700")
LABEL_SIZE = os.environ.get("LABEL_SIZE", "62")  # mm width: 29, 38, 50, 54, 62, 102

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

async def render_label(label_url: str) -> bytes:
    """
    Render the label page with Playwright and screenshot the .label div.
    Returns PNG bytes.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(device_scale_factor=SCREENSHOT_DPI / 96)
        await page.goto(label_url, wait_until="networkidle")

        # Wait for QR code image to load
        await page.wait_for_selector(".label img", timeout=10000)

        element = await page.query_selector(".label")
        if not element:
            await browser.close()
            raise RuntimeError("Could not find .label element on page")

        png_bytes = await element.screenshot()
        await browser.close()
        return png_bytes


# ─────────────────────────────────────────────────────────────────────────────
# Printing
# ─────────────────────────────────────────────────────────────────────────────

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

        image = Image.open(io.BytesIO(png_bytes))

        qlr = BrotherQLRaster(PRINTER_MODEL)
        qlr.exception_on_warning = True

        instructions = convert(
            qlr=qlr,
            images=[image],
            label=LABEL_SIZE,
            rotate="auto",
            threshold=70.0,
            dither=False,
            compress=False,
            red=False,
            dpi_600=False,
            hq=True,
            cut=True,
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
    async with websockets.connect(ws_url, additional_headers=headers) as ws:
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
        png_bytes = await render_label(label_url)

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
# Entry point with reconnect logic
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    backoff = 1
    http_session = None

    while True:
        try:
            if http_session is None:
                http_session = authenticate()
            await run_client(http_session)
            # If we reach here without exception, WS closed cleanly
            backoff = 1
        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException) as exc:
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


if __name__ == "__main__":
    asyncio.run(main())
