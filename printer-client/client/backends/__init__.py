"""Printer backend abstraction.

Each backend (Brother QL, Dymo) is a self-contained module that reads its own
configuration from the environment and implements PrinterBackend. Imports of
the concrete backend are deferred to get_backend() so a machine only needs the
optional dependency for the backend it actually runs (e.g. brother_ql-inventree
is not required when PRINTER_TYPE=dymo, and pywin32 is not required off
Windows). Dymo has two backends — dymo_cups.py (Linux/macOS, via CUPS `lp`)
and dymo_windows.py (via the Windows print driver) — selected by platform.
"""

import sys
from typing import Protocol, runtime_checkable


@runtime_checkable
class PrinterBackend(Protocol):
    def validate_label_size(self, label_size: str) -> None: ...
    def get_label_target_size(self, label_size: str) -> tuple[int, int]: ...
    def discover_printer(self, backend: str, identifier: str) -> str: ...
    def print_png(self, png_bytes: bytes) -> None: ...


def get_backend(printer_type: str) -> PrinterBackend:
    if printer_type == "dymo":
        if sys.platform == "win32":
            from .dymo_windows import DymoBackend
        else:
            from .dymo_cups import DymoBackend

        return DymoBackend()
    from .brother import BrotherBackend

    return BrotherBackend()
