from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Event, Session, Ticket
from .serializers import EventSerializer, SessionSerializer, TicketSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing events.
    Requires authentication.
    """

    queryset = Event.objects.prefetch_related("sessions").all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
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
    Requires authentication.
    """

    queryset = Session.objects.select_related("event").all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "event__name"]
    filterset_fields = ["event", "is_active", "requires_ticket"]
    ordering = ["-start_time"]

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
    ViewSet for managing tickets/passes.
    Requires authentication.
    """

    queryset = Ticket.objects.select_related("child", "session").all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type", "child", "session"]
