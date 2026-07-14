"""Shared, platform-agnostic pieces of the Dymo backends.

Both dymo_cups.py (Linux/macOS, via CUPS `lp`) and dymo_windows.py (via the
Windows print driver) print the same physical label rolls, so the target
pixel sizes and label-size validation must stay identical between them —
this is the single source of truth for both.
"""

# (width_px, height_px) at 300 DPI — long side first. All LabelWriter
# 450/550/5XL models print at 300 DPI.
DYMO_LABEL_SIZES = {
    "30252": (1050, 329),  # 3-1/2" x 1-1/8" address
    "30334": (675, 375),  # 2-1/4" x 1-1/4" multipurpose
    "30256": (1200, 695),  # 4" x 2-5/16" large shipping
    "4xl": (1883, 1233),  # 6" x 4" 5XL shipping
}


class DymoLabelSizeMixin:
    """validate_label_size/get_label_target_size, identical on every OS."""

    def validate_label_size(self, label_size: str) -> None:
        """Fail fast if label_size isn't a known Dymo label identifier."""
        if label_size in DYMO_LABEL_SIZES:
            return
        raise SystemExit(
            f"LABEL_SIZE='{label_size}' is not a known Dymo label.\n"
            f"Valid identifiers: {', '.join(sorted(DYMO_LABEL_SIZES))}"
        )

    def get_label_target_size(self, label_size: str) -> tuple[int, int]:
        """Return the expected (width, height) in pixels for label_size.

        label_size is validated at startup (validate_label_size), so it is a
        known identifier by the time we get here.
        """
        return DYMO_LABEL_SIZES[label_size]
