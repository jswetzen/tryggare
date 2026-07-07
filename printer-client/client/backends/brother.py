"""Brother QL label printer backend (brother_ql-inventree, USB/network/kernel)."""

import io
import logging
import os
import sys

log = logging.getLogger("printer-client")

PRINTER_IDENTIFIER = os.environ.get("PRINTER_IDENTIFIER", "")
PRINTER_BACKEND = os.environ.get("PRINTER_BACKEND", "pyusb")  # pyusb | network | linux_kernel
PRINTER_MODEL = os.environ.get("PRINTER_MODEL", "QL-810W")
LABEL_SIZE = os.environ.get("LABEL_SIZE", "29x90")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

# Pixel sizes (landscape: length x width) for common labels, used when
# brother_ql isn't importable. Keys must be valid brother_ql identifiers.
KNOWN_SIZES = {
    "29x90": (991, 306),
    "62x100": (1164, 618),
    "29x42": (425, 306),
}


class BrotherBackend:
    """Prints via brother_ql-inventree (USB, network, or linux_kernel backend)."""

    def _valid_label_identifiers(self) -> list[str]:
        """All brother_ql label identifiers, or our known-sizes keys as a fallback."""
        try:
            from brother_ql.labels import ALL_LABELS

            return [label.identifier for label in ALL_LABELS]
        except ImportError:
            return list(KNOWN_SIZES)

    def validate_label_size(self, label_size: str) -> None:
        """Fail fast if label_size isn't a real brother_ql label identifier.

        A wrong value (e.g. endless "29" when die-cut "29x90" is loaded, or a typo)
        otherwise prints mis-sized garbage or fails obscurely deep in a print job.
        """
        valid = self._valid_label_identifiers()
        if label_size in valid:
            return
        raise SystemExit(
            f"LABEL_SIZE='{label_size}' is not a known brother_ql label.\n"
            f"It must match the media loaded in the printer. Die-cut labels use a\n"
            f"WIDTHxLENGTH identifier (e.g. 29x90); endless tape uses just the width\n"
            f"(e.g. 29). Note '29' (endless) and '29x90' (die-cut) are different media.\n"
            f"Valid identifiers: {', '.join(sorted(valid))}"
        )

    def get_label_target_size(self, label_size: str) -> tuple[int, int]:
        """
        Return the expected (width, height) in pixels for the rendered label
        based on label_size. Landscape orientation (length x width).
        brother_ql's rotate="90" rotates it to portrait for printing.

        label_size is validated at startup (validate_label_size), so it is a
        known identifier by the time we get here.
        """
        try:
            from brother_ql.labels import ALL_LABELS

            for label in ALL_LABELS:
                if label.identifier == label_size:
                    # dots_printable is (width, length) in portrait
                    # We render landscape: (length, width)
                    return (label.dots_printable[1], label.dots_printable[0])
        except ImportError:
            pass
        # brother_ql unavailable: use our known pixel sizes for common labels.
        return KNOWN_SIZES.get(label_size, (991, 306))

    def print_png(self, png_bytes: bytes) -> None:
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

            if not hasattr(Image, "ANTIALIAS"):
                Image.ANTIALIAS = Image.LANCZOS

            image = Image.open(io.BytesIO(png_bytes))
            target_w, target_h = self.get_label_target_size(LABEL_SIZE)

            log.info(
                "Screenshot %dx%d, target %dx%d (landscape)",
                image.size[0],
                image.size[1],
                target_w,
                target_h,
            )

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

    def check_ipp_usb(self) -> None:
        """Warn if ipp-usb service is active — it causes USB reset loops."""
        import subprocess

        try:
            result = subprocess.run(
                ["systemctl", "is-active", "ipp-usb.service"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip() == "active":
                log.warning("=" * 60)
                log.warning("ipp-usb.service is ACTIVE — this causes USB reset loops!")
                log.warning("Run: sudo systemctl stop ipp-usb.service")
                log.warning("=" * 60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # systemctl not available (e.g. macOS/Windows)

    def discover_printer(self, backend: str, identifier: str) -> str:
        """
        Auto-discover printer if identifier is empty.
        Query printer status and log model/label info.
        Returns the printer identifier to use.
        """
        global PRINTER_IDENTIFIER, PRINTER_BACKEND
        PRINTER_BACKEND = backend

        if backend == "network":
            if not identifier:
                log.error(
                    "PRINTER_IDENTIFIER is required for network backend (e.g. tcp://192.168.1.50)"
                )
                sys.exit(1)
            log.info("Network backend: %s", identifier)
            try:
                from brother_ql.backends.helpers import get_network_status

                status_info = get_network_status(identifier)
                if status_info:
                    log.info("Printer status via SNMP: %s", status_info)
                else:
                    log.warning(
                        "Could not query printer status via SNMP (puresnmp not installed?)"
                    )
            except Exception as exc:
                log.warning("Could not query printer status: %s", exc)
            PRINTER_IDENTIFIER = identifier
            return PRINTER_IDENTIFIER

        try:
            from brother_ql.backends.helpers import discover

            printers = discover(backend)
        except Exception as exc:
            log.warning("Printer discovery failed: %s", exc)
            if not identifier:
                log.error("No PRINTER_IDENTIFIER set and discovery failed")
                sys.exit(1)
            PRINTER_IDENTIFIER = identifier
            return PRINTER_IDENTIFIER

        if not identifier:
            if len(printers) == 1:
                identifier = printers[0]["identifier"]
                log.info("Auto-discovered printer: %s", identifier)
            elif len(printers) == 0:
                log.error(
                    "No printers found via %s backend. Is the printer connected?",
                    backend,
                )
                sys.exit(1)
            else:
                identifiers = [p["identifier"] for p in printers]
                log.error(
                    "Multiple printers found — set PRINTER_IDENTIFIER: %s", identifiers
                )
                sys.exit(1)
        else:
            log.info("Using configured printer: %s", identifier)

        # Query printer status
        try:
            from brother_ql.backends.helpers import get_printer, get_status

            printer = get_printer(identifier, backend)
            status_info = get_status(printer)
            log.info("Printer status: %s", status_info)
            printer.dispose()
        except Exception as exc:
            log.warning("Could not query printer status: %s", exc)

        PRINTER_IDENTIFIER = identifier
        return PRINTER_IDENTIFIER
