"""
WebSocket auth for printer clients.

Staff browsers authenticate over the WebSocket with their Django session cookie
(handled by Channels' ``AuthMiddlewareStack``). Printer clients run on a church
LAN and have no session — they present a revocable per-printer token as a
``?token=`` query param instead. This middleware resolves that token to a
printer row and stashes its id on the scope; the consumer then binds the
connection to exactly that printer, so a client can't claim another printer's
identity.

Order matters: this wraps ``AuthMiddlewareStack`` so ``scope["user"]`` is still
populated for session-authed staff connections. A connection is authorised if
it has either a valid printer token OR an authenticated user.
"""

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async


@database_sync_to_async
def _resolve_printer_id(token: str):
    from printing.models import Printer

    if not token:
        return None
    printer = Printer.objects.filter(token=token, token_revoked_at__isnull=True).first()
    return str(printer.id) if printer else None


class PrinterTokenMiddleware:
    """Resolve a ``?token=`` query param to ``scope['printer_id']``."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["printer_id"] = None

        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        if token:
            scope["printer_id"] = await _resolve_printer_id(token)

        return await self.app(scope, receive, send)


def PrinterTokenAuthStack(app):
    """Printer-token auth layered over the standard session auth stack."""
    return PrinterTokenMiddleware(AuthMiddlewareStack(app))
