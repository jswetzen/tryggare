import io
import logging
import sys
import types
from unittest import mock

import pytest
from PIL import Image

import client.backends.brother as brother
from client.backends.brother import BrotherBackend


def _png_bytes(width, height):
    img = Image.new("RGB", (width, height), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def backend():
    return BrotherBackend()


@pytest.fixture
def mocked_all_labels(monkeypatch, mock_label):
    import brother_ql.labels as labels_module

    labels = [
        mock_label("29x90", (306, 991)),
        mock_label("62x100", (618, 1164)),
    ]
    monkeypatch.setattr(labels_module, "ALL_LABELS", labels)
    return labels


@pytest.fixture
def no_brother_ql_labels(monkeypatch):
    monkeypatch.setitem(sys.modules, "brother_ql.labels", None)


# ─────────────────────────────────────────────────────────────────────────────
# validate_label_size
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_label_size_valid_identifier(backend, mocked_all_labels):
    backend.validate_label_size("29x90")  # no exception


def test_validate_label_size_unknown_identifier_raises(backend, mocked_all_labels):
    with pytest.raises(SystemExit) as exc_info:
        backend.validate_label_size("bogus")
    assert "bogus" in str(exc_info.value)
    assert "29x90" in str(exc_info.value)


def test_validate_label_size_import_error_falls_back_to_known_sizes(
    backend, no_brother_ql_labels
):
    backend.validate_label_size("29x90")  # in KNOWN_SIZES, no exception
    with pytest.raises(SystemExit):
        backend.validate_label_size("not-a-known-size")


# ─────────────────────────────────────────────────────────────────────────────
# get_label_target_size
# ─────────────────────────────────────────────────────────────────────────────


def test_get_label_target_size_landscape_swap(backend, mocked_all_labels):
    # dots_printable=(306, 991) is (width, length) in portrait; landscape swap
    # returns (length, width) = (991, 306)
    assert backend.get_label_target_size("29x90") == (991, 306)


def test_get_label_target_size_import_error_uses_known_sizes(
    backend, no_brother_ql_labels
):
    assert backend.get_label_target_size("62x100") == brother.KNOWN_SIZES["62x100"]


def test_get_label_target_size_unknown_identifier_returns_default(
    backend, mocked_all_labels
):
    assert backend.get_label_target_size("nonexistent") == (991, 306)


# ─────────────────────────────────────────────────────────────────────────────
# print_png
# ─────────────────────────────────────────────────────────────────────────────


def test_print_png_dry_run_skips_hardware(backend, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="printer-client")
    monkeypatch.setattr(brother, "DRY_RUN", True)

    backend.print_png(_png_bytes(10, 10))

    assert any("Would print" in r.message for r in caplog.records)


def _setup_print_mocks(monkeypatch, mocked_all_labels):
    import brother_ql.backends.helpers as helpers_module
    import brother_ql.conversion as conversion_module
    import brother_ql.raster as raster_module

    monkeypatch.setattr(brother, "DRY_RUN", False)
    monkeypatch.setattr(brother, "LABEL_SIZE", "29x90")
    monkeypatch.setattr(brother, "PRINTER_MODEL", "QL-810W")
    monkeypatch.setattr(brother, "PRINTER_IDENTIFIER", "usb://x")
    monkeypatch.setattr(brother, "PRINTER_BACKEND", "pyusb")

    raster_instance = mock.MagicMock()
    raster_class = mock.Mock(return_value=raster_instance)
    convert_mock = mock.Mock(return_value=b"instructions")
    send_mock = mock.Mock()
    resize_mock = mock.Mock(return_value="resized-sentinel")

    monkeypatch.setattr(raster_module, "BrotherQLRaster", raster_class)
    monkeypatch.setattr(conversion_module, "convert", convert_mock)
    monkeypatch.setattr(helpers_module, "send", send_mock)
    monkeypatch.setattr(Image.Image, "resize", resize_mock)

    return types.SimpleNamespace(
        raster_instance=raster_instance,
        raster_class=raster_class,
        convert_mock=convert_mock,
        send_mock=send_mock,
        resize_mock=resize_mock,
    )


def test_print_png_no_resize_when_already_target_size(
    backend, monkeypatch, mocked_all_labels
):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)
    target_w, target_h = backend.get_label_target_size("29x90")

    backend.print_png(_png_bytes(target_w, target_h))

    mocks.resize_mock.assert_not_called()


def test_print_png_resizes_when_wrong_size(backend, monkeypatch, mocked_all_labels):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)
    target_w, target_h = backend.get_label_target_size("29x90")

    backend.print_png(_png_bytes(10, 10))

    mocks.resize_mock.assert_called_once_with((target_w, target_h), Image.LANCZOS)


def test_print_png_creates_raster_with_model_and_exception_on_warning(
    backend, monkeypatch, mocked_all_labels
):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)

    backend.print_png(_png_bytes(10, 10))

    mocks.raster_class.assert_called_once_with("QL-810W")
    assert mocks.raster_instance.exception_on_warning is True


def test_print_png_calls_convert_with_expected_args(
    backend, monkeypatch, mocked_all_labels
):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)

    backend.print_png(_png_bytes(10, 10))

    _, kwargs = mocks.convert_mock.call_args
    assert kwargs["qlr"] is mocks.raster_instance
    assert kwargs["label"] == "29x90"
    assert kwargs["rotate"] == "90"
    assert kwargs["threshold"] == 70.0
    assert kwargs["dither"] is False
    assert kwargs["compress"] is False
    assert kwargs["red"] is False
    assert kwargs["dpi_600"] is False
    assert kwargs["hq"] is True
    assert kwargs["cut"] is False


def test_print_png_calls_send_with_expected_args(
    backend, monkeypatch, mocked_all_labels
):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)

    backend.print_png(_png_bytes(10, 10))

    mocks.send_mock.assert_called_once_with(
        instructions=b"instructions",
        printer_identifier="usb://x",
        backend_identifier="pyusb",
        blocking=True,
    )


def test_print_png_send_exception_propagates(backend, monkeypatch, mocked_all_labels):
    mocks = _setup_print_mocks(monkeypatch, mocked_all_labels)
    mocks.send_mock.side_effect = RuntimeError("printer on fire")

    with pytest.raises(RuntimeError, match="printer on fire"):
        backend.print_png(_png_bytes(10, 10))


# ─────────────────────────────────────────────────────────────────────────────
# discover_printer
# ─────────────────────────────────────────────────────────────────────────────


def test_discover_printer_single_printer_sets_and_returns_identifier(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(
        helpers_module, "discover", lambda backend: [{"identifier": "usb://only"}]
    )
    monkeypatch.setattr(
        helpers_module, "get_printer", lambda identifier, backend: mock.MagicMock()
    )
    monkeypatch.setattr(helpers_module, "get_status", lambda printer: {"ok": True})

    result = backend.discover_printer("pyusb", "")

    assert result == "usb://only"


def test_discover_printer_zero_printers_exits(backend, monkeypatch):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(helpers_module, "discover", lambda backend: [])

    with pytest.raises(SystemExit):
        backend.discover_printer("pyusb", "")


def test_discover_printer_multiple_printers_no_identifier_exits(backend, monkeypatch):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(
        helpers_module,
        "discover",
        lambda backend: [{"identifier": "a"}, {"identifier": "b"}],
    )

    with pytest.raises(SystemExit):
        backend.discover_printer("pyusb", "")


def test_discover_printer_multiple_printers_with_configured_identifier(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(
        helpers_module,
        "discover",
        lambda backend: [{"identifier": "a"}, {"identifier": "b"}],
    )
    monkeypatch.setattr(
        helpers_module, "get_printer", lambda identifier, backend: mock.MagicMock()
    )
    monkeypatch.setattr(helpers_module, "get_status", lambda printer: {"ok": True})

    result = backend.discover_printer("pyusb", "usb://configured")

    assert result == "usb://configured"


def test_discover_printer_network_backend_no_identifier_exits(backend):
    with pytest.raises(SystemExit):
        backend.discover_printer("network", "")


def test_discover_printer_network_backend_with_identifier_queries_status(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    get_network_status_mock = mock.Mock(return_value={"status": "ready"})
    monkeypatch.setattr(
        helpers_module, "get_network_status", get_network_status_mock
    )

    result = backend.discover_printer("network", "tcp://192.168.1.50")

    assert result == "tcp://192.168.1.50"
    get_network_status_mock.assert_called_once_with("tcp://192.168.1.50")


def test_discover_printer_network_backend_status_failure_nonfatal(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(
        helpers_module,
        "get_network_status",
        mock.Mock(side_effect=RuntimeError("snmp down")),
    )

    result = backend.discover_printer("network", "tcp://192.168.1.50")

    assert result == "tcp://192.168.1.50"


def test_discover_printer_discovery_exception_falls_back_to_configured(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    def _raise(backend):
        raise RuntimeError("usb enumeration failed")

    monkeypatch.setattr(helpers_module, "discover", _raise)

    result = backend.discover_printer("pyusb", "usb://configured")

    assert result == "usb://configured"


def test_discover_printer_discovery_exception_no_identifier_exits(
    backend, monkeypatch
):
    import brother_ql.backends.helpers as helpers_module

    def _raise(backend):
        raise RuntimeError("usb enumeration failed")

    monkeypatch.setattr(helpers_module, "discover", _raise)

    with pytest.raises(SystemExit):
        backend.discover_printer("pyusb", "")


def test_discover_printer_status_query_exception_nonfatal(backend, monkeypatch):
    import brother_ql.backends.helpers as helpers_module

    monkeypatch.setattr(
        helpers_module, "discover", lambda backend: [{"identifier": "usb://only"}]
    )
    monkeypatch.setattr(
        helpers_module,
        "get_printer",
        mock.Mock(side_effect=RuntimeError("status query failed")),
    )

    result = backend.discover_printer("pyusb", "")

    assert result == "usb://only"
