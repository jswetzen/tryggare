from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import (
    POST_REQUIRES_CHANGE,
    DjangoModelPermissionsWithView,
    model_permissions,
)

from .models import Event, EventTicket, Session, SessionTicket, Ticket
from .serializers import (
    EventSerializer,
    EventTicketSerializer,
    SessionSerializer,
    SessionTicketSerializer,
    TicketSerializer,
)


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing events.
    Gated on the matching ``events`` model permission (view/add/change/delete);
    a Volontär holds only the ``view_`` half.
    """

    queryset = Event.objects.prefetch_related("sessions").all()
    serializer_class = EventSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    search_fields = ["name"]
    ordering = ["-start_date"]

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """Get all sessions for a specific event"""
        event = self.get_object()
        sessions = event.sessions.all()
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing sessions.
    Gated on the matching ``events`` model permission (view/add/change/delete);
    a Volontär holds only the ``view_`` half.
    """

    queryset = Session.objects.select_related("event").all()
    serializer_class = SessionSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    search_fields = ["name", "event__name"]
    filterset_fields = ["event", "is_active", "requires_ticket"]
    ordering = ["-start_time"]

    # ``activate``/``deactivate`` are POSTs that edit an existing session. Left
    # to the default map they would require ``add_session``, so a role allowed
    # to edit sessions but not create them could not open one — and "can create"
    # would silently also mean "can flip every session's live state". Say what
    # they actually do.
    _toggle_permission = model_permissions(
        Session, perms_map=POST_REQUIRES_CHANGE, name="SessionTogglePermissions"
    )

    def get_permissions(self):
        if self.action in ("activate", "deactivate"):
            return [self._toggle_permission()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate a session"""
        session = self.get_object()
        session.is_active = True
        session.save()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Deactivate a session"""
        session = self.get_object()
        session.is_active = False
        session.save()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get all active sessions"""
        active_sessions = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_sessions, many=True)
        return Response(serializer.data)


class TicketViewSet(viewsets.ModelViewSet):
    """
    DEPRECATED: Use EventTicketViewSet or SessionTicketViewSet instead.
    ViewSet for managing tickets/passes (legacy).
    Gated on the matching ``events`` model permission (view/add/change/delete);
    a Volontär holds only the ``view_`` half.
    """

    queryset = Ticket.objects.select_related("attendee", "session").all()
    serializer_class = TicketSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    filterset_fields = ["type", "attendee", "session"]


class EventTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing event tickets (passes).
    Event tickets grant access to all sessions within an event.
    Gated on the matching ``events`` model permission (view/add/change/delete);
    a Volontär holds only the ``view_`` half.
    """

    queryset = EventTicket.objects.select_related("attendee", "event").all()
    serializer_class = EventTicketSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    filterset_fields = ["attendee", "event"]
    ordering = ["event__start_date"]


class SessionTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing session tickets.
    Session tickets grant access to a specific session only.
    Gated on the matching ``events`` model permission (view/add/change/delete);
    a Volontär holds only the ``view_`` half.
    """

    queryset = SessionTicket.objects.select_related(
        "attendee", "session", "session__event"
    ).all()
    serializer_class = SessionTicketSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    filterset_fields = ["attendee", "session"]
    ordering = ["session__start_time"]
