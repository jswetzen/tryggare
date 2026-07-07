import asyncio
import json
from unittest import mock

import pytest

import client


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send(self, data):
        self.sent.append(json.loads(data))


class FakeConnection(FakeWebSocket):
    """Stands in for the object returned by websockets.connect(...)."""

    def __init__(self, incoming_messages):
        super().__init__()
        self._incoming = list(incoming_messages)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._incoming:
            raise StopAsyncIteration
        return self._incoming.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
# handle_print_job
# ─────────────────────────────────────────────────────────────────────────────


async def test_handle_print_job_success_runs_in_executor_and_sends_completed(
    monkeypatch,
):
    ws = FakeWebSocket()
    mock_loop = mock.Mock()
    mock_loop.run_in_executor = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: mock_loop)

    await client.handle_print_job(ws, "job-1", "http://backend/label/1")

    mock_loop.run_in_executor.assert_called_once()
    assert {"type": "print_job_completed", "job_id": "job-1"} in ws.sent


async def test_handle_print_job_failure_sends_failed_with_reason(monkeypatch):
    ws = FakeWebSocket()
    mock_loop = mock.Mock()
    mock_loop.run_in_executor = mock.AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: mock_loop)

    await client.handle_print_job(ws, "job-1", "http://backend/label/1")

    assert {
        "type": "print_job_failed",
        "job_id": "job-1",
        "reason": "boom",
    } in ws.sent


async def test_handle_print_job_success_releases_job_as_completed(monkeypatch):
    ws = FakeWebSocket()
    mock_loop = mock.Mock()
    mock_loop.run_in_executor = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: mock_loop)

    client._claim_job("job-1")
    await client.handle_print_job(ws, "job-1", "http://backend/label/1")

    # Completed jobs are remembered, so a re-claim is rejected.
    assert client._claim_job("job-1") is False


async def test_handle_print_job_failure_releases_job_for_retry(monkeypatch):
    ws = FakeWebSocket()
    mock_loop = mock.Mock()
    mock_loop.run_in_executor = mock.AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: mock_loop)

    client._claim_job("job-1")
    await client.handle_print_job(ws, "job-1", "http://backend/label/1")

    # Failed jobs are forgotten, so a re-claim (retry) succeeds.
    assert client._claim_job("job-1") is True


# ─────────────────────────────────────────────────────────────────────────────
# run_client
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_client_registers_on_connect(monkeypatch):
    conn = FakeConnection([])
    monkeypatch.setattr(client.websockets, "connect", lambda *a, **k: conn)
    monkeypatch.setattr(client, "PRINTER_NAME", "Test Printer")

    await client.run_client()

    assert conn.sent[0] == {"type": "printer_register", "name": "Test Printer"}


async def test_run_client_sets_my_printer_id_on_registered_self(monkeypatch):
    messages = [
        json.dumps({"type": "printer_registered_self", "data": {"printer_id": "p1"}}),
    ]
    conn = FakeConnection(messages)
    monkeypatch.setattr(client.websockets, "connect", lambda *a, **k: conn)

    dispatched = []

    async def fake_handle_print_job(ws, job_id, label_url):
        dispatched.append(job_id)

    monkeypatch.setattr(client, "handle_print_job", fake_handle_print_job)

    await client.run_client()
    await asyncio.sleep(0)

    assert dispatched == []


async def test_run_client_dispatches_print_job_for_matching_printer(monkeypatch):
    messages = [
        json.dumps({"type": "printer_registered_self", "data": {"printer_id": "p1"}}),
        json.dumps(
            {
                "type": "print_job",
                "data": {
                    "job_id": "j1",
                    "printer_id": "p1",
                    "label_url": "http://x",
                },
            }
        ),
    ]
    conn = FakeConnection(messages)
    monkeypatch.setattr(client.websockets, "connect", lambda *a, **k: conn)

    dispatched = []

    async def fake_handle_print_job(ws, job_id, label_url):
        dispatched.append(job_id)

    monkeypatch.setattr(client, "handle_print_job", fake_handle_print_job)

    await client.run_client()
    await asyncio.sleep(0)

    assert dispatched == ["j1"]


async def test_run_client_skips_print_job_for_other_printer(monkeypatch):
    messages = [
        json.dumps({"type": "printer_registered_self", "data": {"printer_id": "p1"}}),
        json.dumps(
            {
                "type": "print_job",
                "data": {
                    "job_id": "j1",
                    "printer_id": "OTHER",
                    "label_url": "http://x",
                },
            }
        ),
    ]
    conn = FakeConnection(messages)
    monkeypatch.setattr(client.websockets, "connect", lambda *a, **k: conn)

    dispatched = []

    async def fake_handle_print_job(ws, job_id, label_url):
        dispatched.append(job_id)

    monkeypatch.setattr(client, "handle_print_job", fake_handle_print_job)

    await client.run_client()
    await asyncio.sleep(0)

    assert dispatched == []


async def test_run_client_skips_duplicate_job_id(monkeypatch):
    messages = [
        json.dumps({"type": "printer_registered_self", "data": {"printer_id": "p1"}}),
        json.dumps(
            {
                "type": "print_job",
                "data": {
                    "job_id": "j1",
                    "printer_id": "p1",
                    "label_url": "http://x",
                },
            }
        ),
        json.dumps(
            {
                "type": "print_job",
                "data": {
                    "job_id": "j1",
                    "printer_id": "p1",
                    "label_url": "http://x",
                },
            }
        ),
    ]
    conn = FakeConnection(messages)
    monkeypatch.setattr(client.websockets, "connect", lambda *a, **k: conn)

    dispatched = []

    async def fake_handle_print_job(ws, job_id, label_url):
        dispatched.append(job_id)

    monkeypatch.setattr(client, "handle_print_job", fake_handle_print_job)

    await client.run_client()
    await asyncio.sleep(0)

    assert dispatched == ["j1"]  # second delivery of j1 was ignored


# ─────────────────────────────────────────────────────────────────────────────
# heartbeat_loop
# ─────────────────────────────────────────────────────────────────────────────


async def test_heartbeat_loop_sends_heartbeat_on_interval(monkeypatch):
    ws = FakeWebSocket()
    sleep_calls = []

    class _StopLoop(Exception):
        pass

    async def fake_sleep(delay):
        sleep_calls.append(delay)
        if len(sleep_calls) > 1:
            raise _StopLoop()

    monkeypatch.setattr(client.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoop):
        await client.heartbeat_loop(ws)

    assert sleep_calls[0] == 10
    assert {"type": "printer_heartbeat"} in ws.sent
