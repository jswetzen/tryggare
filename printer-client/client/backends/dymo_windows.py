"""Dymo LabelWriter backend via the Windows print driver (GDI) — Windows only.

There's no Windows equivalent of CUPS, so this submits the rendered PNG as a
bitmap print job straight to the printer's normal Windows driver — the same
one used printing from any other app. This mirrors dymo_cups.py's approach
("hand the OS print system a correctly-sized raster and let the driver do the
rest") rather than talking to the printer directly, so it can't run into the
DRM some newer LabelWriter models enforce against unofficial raw protocols.

All pywin32 imports are lazy (inside methods) so this module — and
`get_backend()`'s dispatch check — stays importable on Linux/macOS, where
pywin32 isn't installed (see the `dymo` extra's `sys_platform` marker in
pyproject.toml).
"""

import io
import logging
import os
import sys

from .dymo_common import DymoLabelSizeMixin

log = logging.getLogger("printer-client")

PRINTER_IDENTIFIER = os.environ.get("PRINTER_IDENTIFIER", "")
LABEL_SIZE = os.environ.get("LABEL_SIZE", "30252")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")


class DymoBackend(DymoLabelSizeMixin):
    """Prints via the Windows print driver (win32print/win32gui/win32ui)."""

    def _devmode_for_label_size(self, printer_name: str, label_size: str):
        """Return a DEVMODE with PaperSize set to the driver's form for
        label_size, found by matching the label identifier against the
        driver's own paper-name list (DC_PAPERNAMES/DC_PAPERS) rather than
        hardcoding form names, which vary by driver version/locale.
        """
        import win32con
        import win32print

        handle = win32print.OpenPrinter(printer_name)
        try:
            props = win32print.GetPrinter(handle, 2)
            port = props["pPortName"]
            names = win32print.DeviceCapabilities(
                printer_name, port, win32print.DC_PAPERNAMES
            )
            ids = win32print.DeviceCapabilities(
                printer_name, port, win32print.DC_PAPERS
            )
            match = next(
                (pid for name, pid in zip(names, ids) if label_size in name.lower()),
                None,
            )
            if match is None:
                raise RuntimeError(
                    f"No paper form matching '{label_size}' in the driver's "
                    f"paper list: {list(names)}. Open the printer's Windows "
                    f"properties and confirm that label size is available."
                )
            devmode = props["pDevMode"]
            devmode.PaperSize = match
            devmode.Fields |= win32con.DM_PAPERSIZE
            return devmode
        finally:
            win32print.ClosePrinter(handle)

    def print_png(self, png_bytes: bytes) -> None:
        """Send PNG bytes to the Dymo printer via the Windows print driver.
        Skipped in DRY_RUN mode.
        """
        if DRY_RUN:
            log.info(
                "[DRY RUN] Would print %d bytes via the Windows print driver",
                len(png_bytes),
            )
            return

        import win32gui
        import win32print
        import win32ui
        from PIL import Image, ImageWin

        image = Image.open(io.BytesIO(png_bytes))
        target_w, target_h = self.get_label_target_size(LABEL_SIZE)
        if image.size != (target_w, target_h):
            image = image.resize((target_w, target_h), Image.LANCZOS)

        devmode = self._devmode_for_label_size(PRINTER_IDENTIFIER, LABEL_SIZE)
        hdc = win32gui.CreateDC("WINSPOOL", PRINTER_IDENTIFIER, devmode)
        dc = win32ui.CreateDCFromHandle(hdc)
        try:
            dc.StartDoc("Label")
            dc.StartPage()
            dib = ImageWin.Dib(image)
            dib.draw(dc.GetHandleOutput(), (0, 0, target_w, target_h))
            dc.EndPage()
            dc.EndDoc()
            log.info("Label printed successfully")
        finally:
            dc.DeleteDC()

    def discover_printer(self, backend: str, identifier: str) -> str:
        """Find the Dymo printer among Windows' installed printers.
        `backend` is unused — Dymo always prints through the Windows driver,
        unlike Brother's pyusb/network/linux_kernel choice.
        """
        global PRINTER_IDENTIFIER

        if identifier:
            log.info("Using configured printer: %s", identifier)
            PRINTER_IDENTIFIER = identifier
            return PRINTER_IDENTIFIER

        import win32print

        printers = [
            p["pPrinterName"]
            for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            if "dymo" in p["pPrinterName"].lower()
        ]

        if len(printers) == 1:
            PRINTER_IDENTIFIER = printers[0]
            log.info("Auto-discovered Dymo printer: %s", PRINTER_IDENTIFIER)
            return PRINTER_IDENTIFIER
        if not printers:
            log.error(
                "No Dymo printer found among Windows printers. Is it installed "
                "under Devices & Printers?"
            )
            sys.exit(1)
        log.error("Multiple Dymo printers found — set PRINTER_IDENTIFIER: %s", printers)
        sys.exit(1)
