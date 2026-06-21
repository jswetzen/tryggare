#!/usr/bin/env python3
"""
Printer client for the Conference Child Management System.

Connects to the backend WebSocket, receives print jobs, renders labels
with WeasyPrint + pymupdf, and sends to a Brother QL printer.

Configuration via environment variables (see .env.example).
"""

import argparse
import asyncio
import getpass
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import fitz  # pymupdf
import requests
import websockets
from dotenv import find_dotenv, load_dotenv
from weasyprint import HTML

# Resolve the .env path so we can persist a provisioned token back to it.
DOTENV_PATH = os.environ.get("DOTENV_PATH") or find_dotenv(usecwd=True) or ".env"
load_dotenv(DOTENV_PATH)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
# Per-printer auth token. When blank on first run, the client provisions one:
# it prompts for a staff login interactively (or uses STAFF_USERNAME/PASSWORD
# if those are set), writes the token to .env, and removes any credential lines
# from .env. Can also be set manually (provision in the admin / API).
PRINTER_TOKEN = os.environ.get("PRINTER_TOKEN", "")

# Optional bootstrap credentials. If set, they're used instead of prompting,
# then stripped from .env after the token is minted. Names of the .env keys are
# kept here so persistence can find and remove them.
STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "")
_CRED_ENV_KEYS = ("STAFF_USERNAME", "STAFF_PASSWORD")

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
# Connection
# ─────────────────────────────────────────────────────────────────────────────

def get_ws_url() -> str:
    """Build the authenticated WebSocket URL (BACKEND_URL + printer token)."""
    base = BACKEND_URL.rstrip("/")
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://"):]
    else:
        ws_base = "ws://" + base
    return f"{ws_base}/ws/checkins/?token={quote(PRINTER_TOKEN)}"


# ─────────────────────────────────────────────────────────────────────────────
# Token bootstrap (first run): log in with staff creds, provision a printer +
# token, persist the token to .env. Credentials are not used again afterwards.
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_credentials(non_interactive: bool) -> tuple[str, str]:
    """Get staff credentials to provision with.

    Env vars take precedence (good for scripted setup); otherwise prompt at the
    terminal. Raises RuntimeError when no credentials can be obtained (headless
    or --non-interactive with nothing set).
    """
    if STAFF_USERNAME and STAFF_PASSWORD:
        return STAFF_USERNAME, STAFF_PASSWORD

    if non_interactive or not sys.stdin.isatty():
        raise RuntimeError(
            "No PRINTER_TOKEN and no credentials available. Provide a token, or "
            "run interactively (a TTY) to log in, or set STAFF_USERNAME/"
            "STAFF_PASSWORD."
        )

    print(f"\nNo printer token yet — log in to provision one for '{PRINTER_NAME}'.")
    print(f"Backend: {BACKEND_URL}")
    username = input("Staff username: ").strip()
    password = getpass.getpass("Staff password: ")
    return username, password


def bootstrap_token(username: str, password: str) -> str:
    """Log in with the given staff credentials and provision a printer token."""
    session = requests.Session()
    session.get(f"{BACKEND_URL}/api/csrf/", timeout=15).raise_for_status()
    csrf = session.cookies.get("csrftoken")

    resp = session.post(
        f"{BACKEND_URL}/api/auth/login/",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": csrf, "Referer": BACKEND_URL},
        timeout=15,
    )
    resp.raise_for_status()
    csrf = session.cookies.get("csrftoken")

    resp = session.post(
        f"{BACKEND_URL}/api/printing/printers/provision/",
        json={"name": PRINTER_NAME},
        headers={"X-CSRFToken": csrf, "Referer": BACKEND_URL},
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()["token"]
    log.info("Provisioned printer '%s' and obtained a token", PRINTER_NAME)
    return token


def persist_token_to_env(token: str) -> None:
    """Save the token to .env and strip any bootstrap credential lines.

    Replaces/inserts ``PRINTER_TOKEN=`` and removes ``STAFF_USERNAME``/
    ``STAFF_PASSWORD`` lines — the credentials are not needed once a token
    exists. Other lines and their order are preserved.
    """
    path = Path(DOTENV_PATH)
    token_line = f"PRINTER_TOKEN={token}"
    try:
        existing = path.read_text().splitlines() if path.exists() else []
        out: list[str] = []
        replaced = False
        for line in existing:
            stripped = line.strip()
            if stripped.startswith("PRINTER_TOKEN="):
                out.append(token_line)
                replaced = True
            elif any(stripped.startswith(f"{key}=") for key in _CRED_ENV_KEYS):
                continue  # drop credential lines
            else:
                out.append(line)
        if not replaced:
            out.append(token_line)
        path.write_text("\n".join(out) + "\n")
        log.info("Saved PRINTER_TOKEN to %s (removed any bootstrap credentials)", path)
    except OSError as exc:
        # Non-fatal: the client still runs this session with the in-memory
        # token, but warn that it will re-provision next start.
        log.warning(
            "Could not write token to %s (%s). The token works for this "
            "session but will be re-provisioned on restart.",
            path,
            exc,
        )


def ensure_token(non_interactive: bool) -> None:
    """Make sure PRINTER_TOKEN is set, provisioning + persisting it if needed."""
    global PRINTER_TOKEN
    if PRINTER_TOKEN:
        return
    username, password = _resolve_credentials(non_interactive)
    PRINTER_TOKEN = bootstrap_token(username, password)
    persist_token_to_env(PRINTER_TOKEN)


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

async def run_client() -> None:
    """Open WS, register printer, handle jobs. Raises on disconnect."""
    ws_url = get_ws_url()

    # The server derives our printer identity from the token and tells us our
    # printer_id in a 'printer_registered_self' message. We filter the broadcast
    # print_job stream to that id.
    my_printer_id: str | None = None

    log.info("Connecting to %s", ws_url.split("?")[0])
    async with websockets.connect(ws_url, origin=BACKEND_URL.rstrip("/")) as ws:
        log.info("Connected")

        # Register printer (identity comes from the token; we only send a name)
        await ws.send(json.dumps({
            "type": "printer_register",
            "name": PRINTER_NAME,
        }))

        # Start heartbeat task
        heartbeat_task = asyncio.ensure_future(heartbeat_loop(ws))

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "printer_registered_self":
                    my_printer_id = msg.get("data", {}).get("printer_id")
                    log.info("Registered as printer '%s' (id: %s)", PRINTER_NAME, my_printer_id)
                    continue

                if msg_type == "print_job":
                    data = msg.get("data", {})
                    job_id = data.get("job_id")
                    printer_id = data.get("printer_id")
                    label_url = data.get("label_url")

                    # Only handle jobs assigned to this printer
                    if my_printer_id is None or printer_id != my_printer_id:
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
            await ws.send(json.dumps({"type": "printer_heartbeat"}))
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

async def main(non_interactive: bool = False) -> None:
    log.info("Printer client starting — model=%s, label=%s, backend=%s",
             PRINTER_MODEL, LABEL_SIZE, PRINTER_BACKEND)

    # First run with no token: provision one (interactive login by default, or
    # from STAFF_* env vars). Subsequent runs reuse the saved token. With
    # --non-interactive we never prompt and require a token / env credentials.
    try:
        ensure_token(non_interactive)
    except RuntimeError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        log.error("Could not provision a token: %s", exc)
        sys.exit(1)

    check_ipp_usb()
    discover_and_check_printer()

    log.info("Printer: %s via %s", PRINTER_IDENTIFIER, PRINTER_BACKEND)
    if DRY_RUN:
        log.info("DRY RUN mode — printing will be skipped")

    backoff = 1

    while True:
        try:
            await run_client()
            # If we reach here without exception, WS closed cleanly
            backoff = 1
        except (websockets.ConnectionClosed,
                websockets.WebSocketException) as exc:
            # A 4401 close means the token was rejected (revoked/invalid). If we
            # still have bootstrap credentials, re-provision a fresh one.
            if getattr(exc, "code", None) == 4401:
                if _reprovision_after_rejection():
                    backoff = 1
                    continue
                log.error(
                    "Connection rejected (4401): PRINTER_TOKEN is invalid or "
                    "revoked, and no staff credentials are available to "
                    "re-provision. Set PRINTER_TOKEN or STAFF_USERNAME/"
                    "STAFF_PASSWORD."
                )
            else:
                log.warning("WebSocket disconnected: %s — reconnecting in %ds", exc, backoff)
        except Exception as exc:
            log.error("Unexpected error: %s — reconnecting in %ds", exc, backoff)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


def _reprovision_after_rejection() -> bool:
    """Mint a fresh token after a 4401, if STAFF_* env credentials are set.

    Only env credentials are used here — a long-running daemon must not block on
    an interactive password prompt. Returns True if a new token was obtained.
    """
    global PRINTER_TOKEN
    if not (STAFF_USERNAME and STAFF_PASSWORD):
        return False
    try:
        PRINTER_TOKEN = bootstrap_token(STAFF_USERNAME, STAFF_PASSWORD)
        persist_token_to_env(PRINTER_TOKEN)
        log.info("Re-provisioned a new printer token after rejection")
        return True
    except (RuntimeError, requests.exceptions.RequestException) as exc:
        log.error("Re-provisioning failed: %s", exc)
        return False


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="printer-client",
        description="Label printer client for the Conference Child Management System.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help=(
            "Never prompt for a login. Requires PRINTER_TOKEN (or STAFF_USERNAME/"
            "STAFF_PASSWORD) to already be set; fails fast otherwise. Use for "
            "systemd/container/appliance deployments with no terminal."
        ),
    )
    return parser.parse_args(argv)


def run() -> None:
    args = _parse_args()
    asyncio.run(main(non_interactive=args.non_interactive))


if __name__ == "__main__":
    run()
