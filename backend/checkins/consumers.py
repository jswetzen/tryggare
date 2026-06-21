"""
WebSocket consumer for real-time check-in updates
"""

import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CheckInConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for broadcasting check-in/check-out events to all connected clients.

    Message types (inbound from clients):
    - printer_register: Printer client registers itself
    - printer_heartbeat: Printer client heartbeat
    - print_job_completed: Printer reports job completed
    - print_job_failed: Printer reports job failed

    Message types (outbound to clients):
    - child_checked_in: A child was checked into a session
    - child_checked_out: A child was checked out from a session
    - checkin_undone: A check-in was undone
    - session_started: A new session was activated
    - session_ended: A session was closed
    - print_job: A print job is ready for a printer client
    - printer_status_changed: A printer came online or went offline
    - printer_registered: A printer was registered
    """

    # Maps printer UUID → asyncio.Task for pending offline detection
    _offline_tasks: dict = {}

    async def connect(self):
        """Accept WebSocket connection and add to broadcast group"""
        # Initialise before any early-return so disconnect() is always safe.
        self.room_group_name = None

        # SECURITY: a connection is authorised if it is either a session-authed
        # staff browser OR a printer client presenting a valid token (resolved
        # to scope["printer_id"] by PrinterTokenMiddleware).
        user = self.scope.get("user")
        printer_id = self.scope.get("printer_id")

        is_staff = bool(user and user.is_authenticated)

        if not is_staff and not printer_id:
            # Reject unauthenticated connections
            await self.close(code=4401)  # Custom close code for unauthorized
            return

        # Add this connection to the checkins broadcast group
        self.room_group_name = "checkins_broadcast"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # A token-authed connection is bound to exactly that printer; the UUID in
        # any printer_register message is ignored in favour of this.
        self._authed_printer_id = printer_id
        # Track printer UUID for this connection (set on printer_register)
        self._printer_uuid = None

        # Send connection confirmation
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to check-in updates",
                }
            )
        )

    async def disconnect(self, close_code):
        """Remove from broadcast group on disconnect"""
        if not self.room_group_name:
            # Connection was rejected before joining any group; nothing to clean up.
            return
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Schedule offline detection if this was a printer connection
        if self._printer_uuid:
            printer_uuid = self._printer_uuid
            task = asyncio.ensure_future(self._schedule_printer_offline(printer_uuid))
            CheckInConsumer._offline_tasks[printer_uuid] = task

    async def _schedule_printer_offline(self, printer_uuid):
        """Wait 30s then mark printer offline if not reconnected."""
        await asyncio.sleep(30)
        # If still in offline_tasks dict, no reconnect happened
        if printer_uuid in CheckInConsumer._offline_tasks:
            del CheckInConsumer._offline_tasks[printer_uuid]
            await self._mark_printer_offline(printer_uuid)

    @database_sync_to_async
    def _mark_printer_offline(self, printer_uuid):
        """Mark printer offline and reassign its pending jobs."""
        from printing.models import Printer, PrintJob

        try:
            printer = Printer.objects.get(pk=printer_uuid)
            printer.is_online = False
            printer.save()

            # Reassign pending/sent jobs to unassigned
            PrintJob.objects.filter(
                printer=printer,
                status__in=[PrintJob.STATUS_PENDING, PrintJob.STATUS_SENT],
            ).update(printer=None, status=PrintJob.STATUS_PENDING)

            # Broadcast status change
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "checkins_broadcast",
                {
                    "type": "printer_status_changed",
                    "data": {
                        "uuid": str(printer.id),
                        "name": printer.name,
                        "is_online": False,
                    },
                },
            )
        except Printer.DoesNotExist:
            pass

    async def receive(self, text_data):
        """Handle incoming WebSocket messages from clients."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "printer_register":
            await self._handle_printer_register(data)
        elif msg_type == "printer_heartbeat":
            await self._handle_printer_heartbeat(data)
        elif msg_type == "print_job_completed":
            await self._handle_print_job_completed(data)
        elif msg_type == "print_job_failed":
            await self._handle_print_job_failed(data)

    async def _handle_printer_register(self, data):
        """Handle printer registration.

        The printer identity comes from the auth token (scope["printer_id"]),
        not from the message — a client cannot register as a different printer.
        Connections without a token (i.e. staff browsers) cannot register.
        """
        printer_uuid = self._authed_printer_id
        if not printer_uuid:
            return

        printer_name = data.get("name") or "Unknown Printer"

        # Cancel any pending offline task for this printer UUID
        if printer_uuid in CheckInConsumer._offline_tasks:
            CheckInConsumer._offline_tasks[printer_uuid].cancel()
            del CheckInConsumer._offline_tasks[printer_uuid]

        # Store printer UUID on this connection
        self._printer_uuid = printer_uuid

        # Update the provisioned printer record (name + online status)
        await self._upsert_printer(printer_uuid, printer_name)

        # Tell this client which printer id it is bound to, so it can filter
        # the broadcast print_job stream to its own jobs.
        await self.send(
            text_data=json.dumps(
                {
                    "type": "printer_registered_self",
                    "data": {"printer_id": printer_uuid, "name": printer_name},
                }
            )
        )

        # Broadcast printer registered + status changed
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "printer_registered",
                "data": {
                    "uuid": printer_uuid,
                    "name": printer_name,
                    "is_online": True,
                },
            },
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "printer_status_changed",
                "data": {
                    "uuid": printer_uuid,
                    "name": printer_name,
                    "is_online": True,
                },
            },
        )

    @database_sync_to_async
    def _upsert_printer(self, printer_uuid, printer_name):
        from django.utils import timezone
        from printing.models import Printer

        # The row is provisioned ahead of time (the token belongs to it), so we
        # update rather than create — a token never maps to a missing printer.
        Printer.objects.filter(id=printer_uuid).update(
            name=printer_name,
            is_online=True,
            last_seen_at=timezone.now(),
        )

    async def _handle_printer_heartbeat(self, data):
        """Handle printer heartbeat - update last_seen_at."""
        printer_uuid = self._authed_printer_id
        if not printer_uuid:
            return
        await self._update_printer_last_seen(printer_uuid)

    @database_sync_to_async
    def _update_printer_last_seen(self, printer_uuid):
        from django.utils import timezone
        from printing.models import Printer

        Printer.objects.filter(pk=printer_uuid).update(last_seen_at=timezone.now())

    async def _handle_print_job_completed(self, data):
        """Handle print job completion."""
        job_id = data.get("job_id")
        if not job_id or not self._authed_printer_id:
            return
        checkin_id = await self._set_job_completed(job_id)
        if checkin_id:
            await self.channel_layer.group_send(
                "checkins_broadcast",
                {
                    "type": "print_job_completed",
                    "data": {
                        "job_id": job_id,
                        "record_id": checkin_id,
                    },
                },
            )

    @database_sync_to_async
    def _set_job_completed(self, job_id):
        from django.utils import timezone
        from printing.models import PrintJob
        from checkins.models import CheckInRecord

        now = timezone.now()
        # Only the printer the job is assigned to may complete it.
        updated = PrintJob.objects.filter(
            pk=job_id, printer_id=self._authed_printer_id
        ).update(
            status=PrintJob.STATUS_COMPLETED,
            completed_at=now,
        )
        if not updated:
            return None
        try:
            job = PrintJob.objects.select_related("checkin").get(pk=job_id)
            CheckInRecord.objects.filter(pk=job.checkin_id).update(
                label_printed=True,
                label_printed_at=now,
            )
            return str(job.checkin_id)
        except PrintJob.DoesNotExist:
            return None

    async def _handle_print_job_failed(self, data):
        """Handle print job failure."""
        job_id = data.get("job_id")
        if not job_id or not self._authed_printer_id:
            return
        reason = data.get("reason", "")
        await self._set_job_failed(job_id, reason)

    @database_sync_to_async
    def _set_job_failed(self, job_id, reason):
        from printing.models import PrintJob

        PrintJob.objects.filter(pk=job_id, printer_id=self._authed_printer_id).update(
            status=PrintJob.STATUS_FAILED
        )

    # -------------------------------------------------------------------------
    # Handler methods for each broadcast type (called via group_send)
    # -------------------------------------------------------------------------

    async def child_checked_in(self, event):
        """Broadcast child check-in event to client"""
        await self.send(
            text_data=json.dumps({"type": "child_checked_in", "data": event["data"]})
        )

    async def child_checked_out(self, event):
        """Broadcast child check-out event to client"""
        await self.send(
            text_data=json.dumps({"type": "child_checked_out", "data": event["data"]})
        )

    async def session_started(self, event):
        """Broadcast session start event to client"""
        await self.send(
            text_data=json.dumps({"type": "session_started", "data": event["data"]})
        )

    async def session_ended(self, event):
        """Broadcast session end event to client"""
        await self.send(
            text_data=json.dumps({"type": "session_ended", "data": event["data"]})
        )

    async def checkin_undone(self, event):
        """Broadcast check-in undo event to client"""
        await self.send(
            text_data=json.dumps({"type": "checkin_undone", "data": event["data"]})
        )

    async def checkout_undone(self, event):
        """Broadcast checkout undo event to client"""
        await self.send(
            text_data=json.dumps({"type": "checkout_undone", "data": event["data"]})
        )

    async def print_job(self, event):
        """Forward print job to connected printer clients."""
        await self.send(
            text_data=json.dumps({"type": "print_job", "data": event["data"]})
        )

    async def print_job_completed(self, event):
        """Broadcast print job completion to all clients."""
        await self.send(
            text_data=json.dumps({"type": "print_job_completed", "data": event["data"]})
        )

    async def printer_status_changed(self, event):
        """Broadcast printer status change to all clients."""
        await self.send(
            text_data=json.dumps(
                {"type": "printer_status_changed", "data": event["data"]}
            )
        )

    async def printer_registered(self, event):
        """Broadcast printer registration to all clients."""
        await self.send(
            text_data=json.dumps({"type": "printer_registered", "data": event["data"]})
        )
