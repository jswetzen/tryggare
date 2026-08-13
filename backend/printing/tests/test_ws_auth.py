"""WebSocket auth tests: printer connects with a token, revoked tokens rejected."""

from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings

from config.asgi import application
from printing.models import Printer


# ``config/asgi.py`` wraps the websocket app in Channels'
# ``AllowedHostsOriginValidator``, which rejects an Origin-less connection
# unless ``"*"`` is in ALLOWED_HOSTS. ``WebsocketCommunicator`` never sends an
# Origin header, so without this every connection below is refused at the
# validator — the valid-token tests fail and, worse, the negative tests pass
# vacuously. Pinning ALLOWED_HOSTS here makes the assertions depend on the
# auth path rather than on which settings module the runner happened to load.
@override_settings(ALLOWED_HOSTS=["*"])
class PrinterWebSocketAuthTest(TransactionTestCase):
    async def _connect(self, token):
        communicator = WebsocketCommunicator(
            application, f"/ws/checkins/?token={token}"
        )
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_valid_token_connects(self):
        printer = await database_sync_to_async(Printer.objects.create)(name="P")
        communicator, connected = await self._connect(printer.token)
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_no_token_rejected(self):
        # No token and no session => unauthorized.
        communicator = WebsocketCommunicator(application, "/ws/checkins/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
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
