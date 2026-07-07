"""Tests for the Windows Dymo backend.

pywin32 (win32print/win32gui/win32ui/win32con) isn't installable on this
Linux/macOS dev sandbox, and Pillow's ImageWin is compiled Windows-only (its
Dib class fails to even construct off Windows). So every one of those is
faked via sys.modules injection (win32*) or a direct attribute patch on the
real `PIL` package (ImageWin) — the same lazy-import-mocking technique
test_brother.py's `no_brother_ql_labels` fixture uses for brother_ql.
"""

import io
import logging
import sys
import types
from unittest import mock

import pytest
from PIL import Image

import client.backends.dymo_windows as dymo_windows
from client.backends.dymo_common import DYMO_LABEL_SIZES
from client.backends.dymo_windows import DymoBackend


def _png_bytes(width, height):
    img = Image.new("RGB", (width, height), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def backend():
    return DymoBackend()


@pytest.fixture
def fake_win32print(monkeypatch):
    fake = types.ModuleType("win32print")
    fake.PRINTER_ENUM_LOCAL = 1
    fake.PRINTER_ENUM_CONNECTIONS = 2
    fake.DC_PAPERNAMES = "DC_PAPERNAMES"
    fake.DC_PAPERS = "DC_PAPERS"
    fake.EnumPrinters = mock.Mock(return_value=[])
    fake.OpenPrinter = mock.Mock(return_value="fake-printer-handle")
    fake.ClosePrinter = mock.Mock()
    devmode = types.SimpleNamespace(PaperSize=None, Fields=0)
    fake.GetPrinter = mock.Mock(
        return_value={"pPortName": "PORT1", "pDevMode": devmode}
    )
    fake.DeviceCapabilities = mock.Mock(
        side_effect=lambda name, port, cap: {
            "DC_PAPERNAMES": ["30252 Address Labels", "30334 Multipurpose"],
            "DC_PAPERS": [1, 2],
        }[cap]
    )
    monkeypatch.setitem(sys.modules, "win32print", fake)
    return fake


@pytest.fixture
def fake_win32con(monkeypatch):
    fake = types.ModuleType("win32con")
    fake.DM_PAPERSIZE = 2
    monkeypatch.setitem(sys.modules, "win32con", fake)
    return fake


@pytest.fixture
def fake_win32gui_ui(monkeypatch):
    dc_mock = mock.MagicMock()
    win32gui_fake = types.ModuleType("win32gui")
    win32gui_fake.CreateDC = mock.Mock(return_value="fake-hdc")
    win32ui_fake = types.ModuleType("win32ui")
    win32ui_fake.CreateDCFromHandle = mock.Mock(return_value=dc_mock)
    monkeypatch.setitem(sys.modules, "win32gui", win32gui_fake)
    monkeypatch.setitem(sys.modules, "win32ui", win32ui_fake)
    return types.SimpleNamespace(win32gui=win32gui_fake, win32ui=win32ui_fake, dc=dc_mock)


@pytest.fixture
def fake_imagewin(monkeypatch):
    import PIL

    dib_instance = mock.MagicMock()
    fake_module = types.ModuleType("PIL.ImageWin")
    fake_module.Dib = mock.Mock(return_value=dib_instance)
    # Patching the attribute directly (not just sys.modules) is what makes
    # `from PIL import ImageWin` pick this up, and monkeypatch reverts it
    # cleanly — sys.modules injection alone would leak a stale ImageWin
    # attribute onto the real PIL package for the rest of the test session.
    monkeypatch.setattr(PIL, "ImageWin", fake_module, raising=False)
    return fake_module, dib_instance


# ─────────────────────────────────────────────────────────────────────────────
# validate_label_size / get_label_target_size (shared with dymo_cups via
# DymoLabelSizeMixin — just confirm the Windows backend wires it up)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("label_size", ["30252", "30334", "30256", "4xl"])
def test_validate_label_size_known_identifiers(backend, label_size):
    backend.validate_label_size(label_size)  # no exception


def test_validate_label_size_unknown_raises(backend):
    with pytest.raises(SystemExit):
        backend.validate_label_size("bogus")


def test_get_label_target_size_matches_known_sizes(backend):
    for label_size, size in DYMO_LABEL_SIZES.items():
        assert backend.get_label_target_size(label_size) == size


# ─────────────────────────────────────────────────────────────────────────────
# discover_printer
# ─────────────────────────────────────────────────────────────────────────────


def test_discover_printer_returns_configured_identifier(backend, fake_win32print):
    result = backend.discover_printer("", "DYMO LabelWriter 450")

    assert result == "DYMO LabelWriter 450"
    fake_win32print.EnumPrinters.assert_not_called()


def test_discover_printer_single_match(backend, fake_win32print):
    fake_win32print.EnumPrinters.return_value = [
        {"pPrinterName": "DYMO LabelWriter 450"},
        {"pPrinterName": "HP LaserJet"},
    ]

    result = backend.discover_printer("", "")

    assert result == "DYMO LabelWriter 450"


def test_discover_printer_no_match_exits(backend, fake_win32print):
    fake_win32print.EnumPrinters.return_value = [{"pPrinterName": "HP LaserJet"}]

    with pytest.raises(SystemExit):
        backend.discover_printer("", "")


def test_discover_printer_multiple_matches_exits(backend, fake_win32print):
    fake_win32print.EnumPrinters.return_value = [
        {"pPrinterName": "DYMO LabelWriter 450"},
        {"pPrinterName": "DYMO LabelWriter 550"},
    ]

    with pytest.raises(SystemExit):
        backend.discover_printer("", "")


# ─────────────────────────────────────────────────────────────────────────────
# print_png
# ─────────────────────────────────────────────────────────────────────────────


def test_print_png_dry_run_skips_driver(backend, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="printer-client")
    monkeypatch.setattr(dymo_windows, "DRY_RUN", True)

    backend.print_png(_png_bytes(10, 10))

    assert any("Would print" in r.message for r in caplog.records)


def _configure_print_env(monkeypatch, label_size="30252"):
    monkeypatch.setattr(dymo_windows, "DRY_RUN", False)
    monkeypatch.setattr(dymo_windows, "LABEL_SIZE", label_size)
    monkeypatch.setattr(dymo_windows, "PRINTER_IDENTIFIER", "DYMO LabelWriter 450")


def test_print_png_finds_matching_paper_form_and_prints(
    backend, monkeypatch, fake_win32print, fake_win32con, fake_win32gui_ui, fake_imagewin
):
    _configure_print_env(monkeypatch, "30252")

    backend.print_png(_png_bytes(1050, 329))

    devmode = fake_win32print.GetPrinter.return_value["pDevMode"]
    assert devmode.PaperSize == 1  # matches "30252 Address Labels" -> id 1
    assert devmode.Fields == fake_win32con.DM_PAPERSIZE

    fake_win32gui_ui.win32gui.CreateDC.assert_called_once_with(
        "WINSPOOL", "DYMO LabelWriter 450", devmode
    )
    dc = fake_win32gui_ui.dc
    dc.StartDoc.assert_called_once()
    dc.StartPage.assert_called_once()
    dc.EndPage.assert_called_once()
    dc.EndDoc.assert_called_once()
    dc.DeleteDC.assert_called_once()


def test_print_png_no_matching_paper_form_raises(
    backend, monkeypatch, fake_win32print, fake_win32con, fake_win32gui_ui, fake_imagewin
):
    _configure_print_env(monkeypatch, "4xl")  # not in the fake driver's paper list

    with pytest.raises(RuntimeError, match="No paper form matching"):
        backend.print_png(_png_bytes(1883, 1233))


def test_print_png_resizes_when_wrong_size(
    backend, monkeypatch, fake_win32print, fake_win32con, fake_win32gui_ui, fake_imagewin
):
    _configure_print_env(monkeypatch, "30252")

    resize_mock = mock.Mock(return_value="resized-sentinel")
    monkeypatch.setattr(Image.Image, "resize", resize_mock)

    backend.print_png(_png_bytes(10, 10))

    resize_mock.assert_called_once_with((1050, 329), Image.LANCZOS)


def test_print_png_no_resize_when_already_target_size(
    backend, monkeypatch, fake_win32print, fake_win32con, fake_win32gui_ui, fake_imagewin
):
    _configure_print_env(monkeypatch, "30252")

    resize_mock = mock.Mock()
    monkeypatch.setattr(Image.Image, "resize", resize_mock)

    backend.print_png(_png_bytes(1050, 329))

    resize_mock.assert_not_called()
