"""
WebSocket consumer for real-time check-in updates
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CheckInConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for broadcasting check-in/check-out events to all connected clients.

    Message types:
    - child_checked_in: A child was checked into a session
    - child_checked_out: A child was checked out from a session
    - checkin_undone: A check-in was undone
    - session_started: A new session was activated
    - session_ended: A session was closed
    """

    async def connect(self):
        """Accept WebSocket connection and add to broadcast group"""
        # SECURITY: Enforce authentication for WebSocket connections
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            # Reject unauthenticated connections
            await self.close(code=4401)  # Custom close code for unauthorized
            return

        # Add this connection to the checkins broadcast group
        self.room_group_name = "checkins_broadcast"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to check-in updates"
        }))

    async def disconnect(self, close_code):
        """Remove from broadcast group on disconnect"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages (currently not used)"""
        # Future: Could handle client-initiated actions here
        pass

    # Handler methods for each broadcast type
    async def child_checked_in(self, event):
        """Broadcast child check-in event to client"""
        await self.send(text_data=json.dumps({
            "type": "child_checked_in",
            "data": event["data"]
        }))

    async def child_checked_out(self, event):
        """Broadcast child check-out event to client"""
        await self.send(text_data=json.dumps({
            "type": "child_checked_out",
            "data": event["data"]
        }))

    async def session_started(self, event):
        """Broadcast session start event to client"""
        await self.send(text_data=json.dumps({
            "type": "session_started",
            "data": event["data"]
        }))

    async def session_ended(self, event):
        """Broadcast session end event to client"""
        await self.send(text_data=json.dumps({
            "type": "session_ended",
            "data": event["data"]
        }))

    async def checkin_undone(self, event):
        """Broadcast check-in undo event to client"""
        await self.send(text_data=json.dumps({
            "type": "checkin_undone",
            "data": event["data"]
        }))
