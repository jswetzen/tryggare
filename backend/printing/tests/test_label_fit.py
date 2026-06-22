"""
Unit tests for the server-side label name auto-fit (``fit_child_name_pt``).

WeasyPrint (the label renderer in the printer-client) runs no JavaScript and
renders @media print, so the child-name font size is computed here instead of in
CSS. These tests pin the behaviour we care about: short names expand to the cap,
long names shrink to fit the space left beside the QR code, and the result stays
within bounds.
"""

from django.test import SimpleTestCase

from printing.views import (
    _NAME_MAX_PT,
    _NAME_MIN_PT,
    LABEL_DIMENSIONS,
    fit_child_name_pt,
)

# The default die-cut label used in the field.
_W, _H = LABEL_DIMENSIONS["29x90"]["w_mm"], LABEL_DIMENSIONS["29x90"]["h_mm"]


class FitChildNamePtTest(SimpleTestCase):
    def test_short_name_expands_to_max(self):
        # A short name should fill the label, not sit at some small fixed size.
        self.assertEqual(fit_child_name_pt("Bo", _W, _H), _NAME_MAX_PT)

    def test_long_name_shrinks_below_max(self):
        small = fit_child_name_pt("Maximiliana", _W, _H)
        self.assertLess(small, _NAME_MAX_PT)
        self.assertGreaterEqual(small, _NAME_MIN_PT)

    def test_longer_name_is_not_larger_than_shorter_name(self):
        # Monotonic: adding characters never grows the font.
        self.assertGreaterEqual(
            fit_child_name_pt("Anna", _W, _H),
            fit_child_name_pt("Alexander", _W, _H),
        )

    def test_result_never_below_min(self):
        # Even an absurdly long name is clamped, not driven to zero.
        pt = fit_child_name_pt("Wolfeschlegelsteinhausenbergerdorff", _W, _H)
        self.assertGreaterEqual(pt, _NAME_MIN_PT)

    def test_empty_name_returns_min(self):
        self.assertEqual(fit_child_name_pt("", _W, _H), _NAME_MIN_PT)
        self.assertEqual(fit_child_name_pt(None, _W, _H), _NAME_MIN_PT)

    def test_case_insensitive(self):
        # The label is uppercased, so case must not change the fit.
        self.assertEqual(
            fit_child_name_pt("alexander", _W, _H),
            fit_child_name_pt("ALEXANDER", _W, _H),
        )

    def test_narrow_label_constrains_size(self):
        # A short label (17x54) has little height; the same name fits smaller
        # there than on the taller 29x90 label.
        narrow_w = LABEL_DIMENSIONS["17x54"]["w_mm"]
        narrow_h = LABEL_DIMENSIONS["17x54"]["h_mm"]
        self.assertLess(
            fit_child_name_pt("Alexander", narrow_w, narrow_h),
            fit_child_name_pt("Alexander", _W, _H),
        )
