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
    - session_started: A new session was activated
    - session_ended: A session was closed
    """

    async def connect(self):
        """Accept WebSocket connection and add to broadcast group"""
        # Check if user is authenticated
        user = self.scope.get("user")

        # For now, allow anonymous connections (will implement auth later if needed)
        # if not user or not user.is_authenticated:
        #     await self.close()
        #     return

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
