"""WebSocket for the event assistant: one chat per (event, user); protocol in
docs/event-assistant-plan.md, "WebSocket protocol"."""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from events.models import Event

from . import runner
from .models import AssistantConversation, LLMProvider
from .permissions import (
    NOT_AUTHENTICATED,
    can_use_assistant,
    fresh_user,
    lacks_permission,
)

MAX_TEXT_CHARS = 4000
MAX_ID_CHARS = 64

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NO_EVENT = 4404
CLOSE_NOT_ELIGIBLE = 4409
CLOSE_NOT_ENABLED = 4503


@database_sync_to_async
def _connect_checks(user, event_id):
    """``(close_code, event, conversation, ready_fields)``; close_code None when fine."""
    fresh = fresh_user(user) if user is not None and user.is_authenticated else None
    # Permission before the event lookup, so a non-staff user cannot probe event ids.
    reason = lacks_permission(fresh)
    if reason:
        return (
            CLOSE_UNAUTHENTICATED if reason == NOT_AUTHENTICATED else CLOSE_FORBIDDEN,
            None,
            None,
            None,
        )
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        return CLOSE_NO_EVENT, None, None, None
    ok, issues = can_use_assistant(fresh, event)
    if not ok:
        return CLOSE_NOT_ELIGIBLE, None, None, None
    if not LLMProvider.load().enabled:
        return CLOSE_NOT_ENABLED, None, None, None
    conv, _ = AssistantConversation.objects.get_or_create(event=event, user=fresh)
    running = runner.reset_if_dead(conv)
    return (
        None,
        event,
        conv,
        {
            "type": "ready",
            "conversation_id": str(conv.id),
            "running": running,
            "draft_version": conv.draft_version,
            "notice_required": conv.notice_accepted_at is None,
        },
    )


@database_sync_to_async
def _recheck(user, event_id):
    """Per-message re-check: ``(user, event, reason)``; reason is a run_failed code."""
    fresh = fresh_user(user)
    event = Event.objects.filter(pk=event_id).first()
    if fresh is None or event is None or not can_use_assistant(fresh, event)[0]:
        return None, None, "blocked"
    if not LLMProvider.load().enabled:
        return None, None, "not_enabled"
    return fresh, event, None


class AssistantConsumer(AsyncWebsocketConsumer):
    # Tests set a pydantic-ai model here; production leaves it None (the saved provider).
    model = None

    async def connect(self):
        self.group = None
        self.user = self.scope.get("user")
        self.event_id = self.scope["url_route"]["kwargs"]["event_id"]
        code, event, conv, ready = await _connect_checks(self.user, self.event_id)
        if code:
            await self.close(code=code)
            return
        self.event_pk = event.pk
        self.group = f"assistant_{conv.id.hex}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self._send(ready)

    async def disconnect(self, close_code):
        # The run is not tied to this connection; it goes on and others still see it.
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def _send(self, payload: dict):
        await self.send(text_data=json.dumps(payload))

    async def _publish(self, payload: dict):
        await self.channel_layer.group_send(
            self.group, {"type": "assistant.event", "payload": payload}
        )

    async def assistant_event(self, message):
        await self._send(message["payload"])

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "")
        except ValueError:
            data = None
        kind = data.get("type") if isinstance(data, dict) else None
        if kind == "cancel":
            runner.request_cancel(self.event_pk, self.user.pk)
        elif kind == "user_message":
            await self._user_message(data)
        else:
            await self._send({"type": "error", "code": "bad_request"})

    async def _user_message(self, data: dict):
        msg_id, text = data.get("id"), data.get("text")
        if (
            not isinstance(msg_id, str)
            or not 0 < len(msg_id) <= MAX_ID_CHARS
            or not isinstance(text, str)
            or not 0 < len(text.strip()) <= MAX_TEXT_CHARS
        ):
            await self._send({"type": "error", "code": "bad_request"})
            return
        user, event, reason = await _recheck(self.user, self.event_id)
        if reason:
            await self._send(_failed(msg_id, reason))
            return
        runner.start_run(
            event,
            user,
            text.strip(),
            reply_to=msg_id,
            publish=self._publish,
            refuse=self._send,
            model=self.model,
        )


def _failed(reply_to, code):
    return {"type": "run_failed", "run_id": None, "reply_to": reply_to, "code": code}
