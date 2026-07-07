import logging
import subprocess
from unittest import mock

import pytest

import client.backends.dymo as dymo
from client.backends.dymo import DymoBackend


@pytest.fixture
def backend():
    return DymoBackend()


# ─────────────────────────────────────────────────────────────────────────────
# validate_label_size
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("label_size", ["30252", "30334", "30256", "4xl"])
def test_validate_label_size_known_identifiers(backend, label_size):
    backend.validate_label_size(label_size)  # no exception


def test_validate_label_size_unknown_raises(backend):
    with pytest.raises(SystemExit) as exc_info:
        backend.validate_label_size("bogus")
    assert "bogus" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# get_label_target_size
# ─────────────────────────────────────────────────────────────────────────────


def test_get_label_target_size_matches_known_sizes(backend):
    for label_size, size in dymo.DYMO_LABEL_SIZES.items():
        assert backend.get_label_target_size(label_size) == size


# ─────────────────────────────────────────────────────────────────────────────
# print_png
# ─────────────────────────────────────────────────────────────────────────────


def test_print_png_dry_run_skips_subprocess(backend, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="printer-client")
    monkeypatch.setattr(dymo, "DRY_RUN", True)
    run_mock = mock.Mock()
    monkeypatch.setattr(dymo.subprocess, "run", run_mock)

    backend.print_png(b"fake-png-bytes")

    run_mock.assert_not_called()
    assert any("Would print" in r.message for r in caplog.records)


def test_print_png_calls_lp_with_expected_args(backend, monkeypatch):
    monkeypatch.setattr(dymo, "DRY_RUN", False)
    monkeypatch.setattr(dymo, "LABEL_SIZE", "30252")
    monkeypatch.setattr(dymo, "PRINTER_IDENTIFIER", "DYMO_LabelWriter_450")

    run_mock = mock.Mock(return_value=mock.Mock(returncode=0))
    monkeypatch.setattr(dymo.subprocess, "run", run_mock)

    backend.print_png(b"fake-png-bytes")

    run_mock.assert_called_once()
    args, kwargs = run_mock.call_args
    cmd = args[0]
    assert cmd[0] == "lp"
    assert cmd[1:4] == ["-d", "DYMO_LabelWriter_450", "-o"]
    assert "PageSize=w252h79" in cmd
    assert "ppi=300" in cmd
    assert kwargs["check"] is True


def test_print_png_deletes_temp_file_even_when_subprocess_raises(
    backend, monkeypatch
):
    monkeypatch.setattr(dymo, "DRY_RUN", False)
    monkeypatch.setattr(dymo, "LABEL_SIZE", "30252")
    monkeypatch.setattr(dymo, "PRINTER_IDENTIFIER", "DYMO_LabelWriter_450")
    monkeypatch.setattr(
        dymo.subprocess,
        "run",
        mock.Mock(side_effect=subprocess.CalledProcessError(1, ["lp"])),
    )

    unlinked_paths = []
    real_unlink = dymo.os.unlink

    def spy_unlink(path):
        unlinked_paths.append(path)
        real_unlink(path)

    monkeypatch.setattr(dymo.os, "unlink", spy_unlink)

    with pytest.raises(subprocess.CalledProcessError):
        backend.print_png(b"fake-png-bytes")

    assert len(unlinked_paths) == 1
    assert not dymo.os.path.exists(unlinked_paths[0])


# ─────────────────────────────────────────────────────────────────────────────
# discover_printer
# ─────────────────────────────────────────────────────────────────────────────


def test_discover_printer_returns_configured_identifier(backend, monkeypatch):
    run_mock = mock.Mock()
    monkeypatch.setattr(dymo.subprocess, "run", run_mock)

    result = backend.discover_printer("", "DYMO_LabelWriter_450")

    assert result == "DYMO_LabelWriter_450"
    run_mock.assert_not_called()


def test_discover_printer_parses_lpstat_single_match(backend, monkeypatch):
    lpstat_output = (
        "printer DYMO_LabelWriter_450 is idle.  enabled since Mon 01 Jan 2026\n"
        "printer HP_LaserJet is idle.  enabled since Mon 01 Jan 2026\n"
    )
    monkeypatch.setattr(
        dymo.subprocess,
        "run",
        mock.Mock(return_value=mock.Mock(stdout=lpstat_output)),
    )

    result = backend.discover_printer("", "")

    assert result == "DYMO_LabelWriter_450"


def test_discover_printer_no_match_exits(backend, monkeypatch):
    lpstat_output = "printer HP_LaserJet is idle.  enabled since Mon 01 Jan 2026\n"
    monkeypatch.setattr(
        dymo.subprocess,
        "run",
        mock.Mock(return_value=mock.Mock(stdout=lpstat_output)),
    )

    with pytest.raises(SystemExit):
        backend.discover_printer("", "")


def test_discover_printer_lpstat_missing_exits(backend, monkeypatch):
    monkeypatch.setattr(
        dymo.subprocess, "run", mock.Mock(side_effect=FileNotFoundError())
    )

    with pytest.raises(SystemExit):
        backend.discover_printer("", "")
