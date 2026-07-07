"""Dymo LabelWriter backend via CUPS (`lp` subprocess) — Linux/macOS.

No Python driver equivalent to brother_ql exists for Dymo; the pragmatic
approach is to hand the rendered PNG to CUPS. Label sizes are sourced from
the official Dymo CUPS PPD (landscape orientation, long side first); see
dymo_common.py for the pixel dimensions shared with dymo_windows.py.
"""

import logging
import os
import subprocess
import sys
import tempfile

from .dymo_common import DymoLabelSizeMixin

log = logging.getLogger("printer-client")

PRINTER_IDENTIFIER = os.environ.get("PRINTER_IDENTIFIER", "")
LABEL_SIZE = os.environ.get("LABEL_SIZE", "30252")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

DYMO_PPD_SIZES = {
    "30252": "w252h79",
    "30334": "w162h90",
    "30256": "w288h167",
    "4xl": "w452h296",
}


class DymoBackend(DymoLabelSizeMixin):
    """Prints via CUPS (`lp`) to a registered Dymo LabelWriter queue."""

    def print_png(self, png_bytes: bytes) -> None:
        """Send PNG bytes to the Dymo printer via `lp`. Skipped in DRY_RUN."""
        if DRY_RUN:
            log.info("[DRY RUN] Would print %d bytes via CUPS lp", len(png_bytes))
            return

        ppd_size = DYMO_PPD_SIZES.get(LABEL_SIZE, LABEL_SIZE)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_bytes)
            tmp = f.name
        try:
            subprocess.run(
                [
                    "lp",
                    "-d",
                    PRINTER_IDENTIFIER,
                    "-o",
                    f"PageSize={ppd_size}",
                    "-o",
                    "ppi=300",
                    "-o",
                    "PrintQuality=Graphics",
                    tmp,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("Label printed successfully")
        finally:
            os.unlink(tmp)

    def discover_printer(self, backend: str, identifier: str) -> str:
        """Find the Dymo CUPS queue. `backend` is unused — Dymo always goes
        through CUPS, unlike Brother's pyusb/network/linux_kernel choice."""
        global PRINTER_IDENTIFIER

        if identifier:
            log.info("Using configured printer: %s", identifier)
            PRINTER_IDENTIFIER = identifier
            return PRINTER_IDENTIFIER

        try:
            result = subprocess.run(
                ["lpstat", "-p"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as exc:
            log.error("Could not query CUPS printers via lpstat: %s", exc)
            sys.exit(1)

        matches = [
            line.split()[1]
            for line in result.stdout.splitlines()
            if line.startswith("printer ") and "dymo" in line.lower()
        ]

        if len(matches) == 1:
            PRINTER_IDENTIFIER = matches[0]
            log.info("Auto-discovered Dymo printer: %s", PRINTER_IDENTIFIER)
            return PRINTER_IDENTIFIER
        if not matches:
            log.error("No Dymo printer found via CUPS (lpstat -p). Is it registered?")
            sys.exit(1)
        log.error("Multiple Dymo printers found — set PRINTER_IDENTIFIER: %s", matches)
        sys.exit(1)
