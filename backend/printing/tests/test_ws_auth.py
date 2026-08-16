"""WebSocket auth tests: printer connects with a token, revoked tokens rejected."""

from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.conf import settings
from django.test import TransactionTestCase

from config.asgi import application
from printing.models import Printer


def _origin_headers():
    """An Origin header the deployed app's origin validator will accept.

    ``config/asgi.py`` wraps the websocket app in Channels'
    ``AllowedHostsOriginValidator``, which refuses any connection whose Origin
    header is absent or not in ``ALLOWED_HOSTS``.

    These tests used to send no Origin at all and lean on
    ``@override_settings(ALLOWED_HOSTS=["*"])`` instead. That stopped working:
    as of Channels 4 (4.3.2 here) ``AllowedHostsOriginValidator`` is a *factory
    function*, not a class — it reads ``settings.ALLOWED_HOSTS`` once, at the
    moment ``config.asgi`` is imported and ``application`` is built, and bakes
    the list into the returned ``OriginValidator``. It used to be a class that
    re-read the setting on every connection, which is what made
    ``override_settings`` bite. Since ``application`` is constructed at import
    time, long before any ``override_settings`` context is entered, the
    override can no longer reach the validator, and every connection here was
    denied with close code 1000 by ``WebsocketDenier``. The valid-token tests
    failed on that; the two rejection tests kept passing *vacuously*, never
    reaching the auth path they claim to cover.

    Sending a real Origin fixes it at the right level and is also the more
    faithful test: the actual printer client sends one too (``origin=`` in
    ``printer-client/client/__init__.py``), so this now exercises the same code
    path a church-LAN printer does. ``config/settings/base.py`` guarantees
    ``"testserver"`` is in ``ALLOWED_HOSTS`` whenever the list is not the
    wildcard, so this resolves for every settings module the runners use.
    """
    hosts = settings.ALLOWED_HOSTS
    host = "testserver" if ("*" in hosts or "testserver" in hosts) else hosts[0]
    return [(b"origin", f"http://{host}".encode())]


class PrinterWebSocketAuthTest(TransactionTestCase):
    def _communicator(self, path):
        return WebsocketCommunicator(application, path, headers=_origin_headers())

    async def _connect(self, token):
        communicator = self._communicator(f"/ws/checkins/?token={token}")
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_origin_is_accepted_without_credentials(self):
        """Guard: the Origin header alone must not be what fails a connection.

        Without this, a regression in ``_origin_headers`` (or another change to
        the origin validator) would silently turn every rejection test below
        into a vacuous pass again. ``WebsocketDenier`` closes with 1000; the
        consumer's own "unauthorized" close code is 4401, so asserting the code
        distinguishes "rejected by auth" from "never got that far".
        """
        communicator = self._communicator("/ws/checkins/?token=not-a-real-token")
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)
        await communicator.disconnect()

    async def test_valid_token_connects(self):
        printer = await database_sync_to_async(Printer.objects.create)(name="P")
        communicator, connected = await self._connect(printer.token)
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_no_token_rejected(self):
        # No token and no session => unauthorized.
        communicator = self._communicator("/ws/checkins/")
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)
        await communicator.disconnect()

    async def test_revoked_token_rejected(self):
        printer = await database_sync_to_async(Printer.objects.create)(name="P")
        await database_sync_to_async(printer.revoke_token)()
        communicator, connected = await self._connect(printer.token)
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_register_binds_to_token_printer(self):
        """A spoofed UUID in printer_register is ignored; identity is the token's."""
        printer = await database_sync_to_async(Printer.objects.create)(name="Original")
        communicator, connected = await self._connect(printer.token)
        self.assertTrue(connected)

        # Drain the connection_established frame.
        await communicator.receive_json_from()

        await communicator.send_json_to(
            {"type": "printer_register", "uuid": "spoofed", "name": "Renamed"}
        )
        # Server confirms our bound identity with our real printer id.
        reply = await communicator.receive_json_from()
        self.assertEqual(reply["type"], "printer_registered_self")
        self.assertEqual(reply["data"]["printer_id"], str(printer.id))

        await communicator.disconnect()
