from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from events.models import EventTicket, SessionTicket
from .models import Child, Family, Parent
from .serializers import (
    ChildSerializer,
    FamilyCreateSerializer,
    FamilyDetailSerializer,
    FamilySerializer,
    ParentSerializer,
)


class FamilyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing families.
    Requires authentication for all actions.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optimize queries with prefetch_related to avoid N+1 problems.
        Includes ticket information and check-in status for children.
        """
        from checkins.models import CheckInRecord

        event_ticket_prefetch = Prefetch(
            'children__event_tickets',
            queryset=EventTicket.objects.select_related('event')
        )
        session_ticket_prefetch = Prefetch(
            'children__session_tickets',
            queryset=SessionTicket.objects.select_related('session', 'session__event')
        )
        # Prefetch active check-ins for children to avoid N+1 queries
        active_checkins_prefetch = Prefetch(
            'children__checkin_records',
            queryset=CheckInRecord.objects.filter(check_out_time__isnull=True),
            to_attr='active_checkins'
        )

        return Family.objects.prefetch_related(
            "parents",
            "children",
            event_ticket_prefetch,
            session_ticket_prefetch,
            active_checkins_prefetch,
        ).all()

    def get_serializer_class(self):
        if self.action == "create":
            return FamilyCreateSerializer
        if self.action == "retrieve":
            return FamilyDetailSerializer
        return FamilySerializer

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        """Get all children for a specific family"""
        family = self.get_object()
        children = family.children.all()
        serializer = ChildSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def parents(self, request, pk=None):
        """Get all parents for a specific family"""
        family = self.get_object()
        parents = family.parents.all()
        serializer = ParentSerializer(parents, many=True)
        return Response(serializer.data)


class ParentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing parents.
    Requires authentication.
    """

    queryset = Parent.objects.select_related("family").all()
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "email", "phone"]
    filterset_fields = ["family", "relationship_type"]


class ChildViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing children.
    Requires authentication for most actions.
    """

    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name", "qr_token"]
    filterset_fields = ["family"]

    def get_queryset(self):
        """
        Optimize queries with select_related and prefetch_related.
        Includes ticket information to avoid N+1 queries.
        """
        event_ticket_prefetch = Prefetch(
            'event_tickets',
            queryset=EventTicket.objects.select_related('event')
        )
        session_ticket_prefetch = Prefetch(
            'session_tickets',
            queryset=SessionTicket.objects.select_related('session', 'session__event')
        )

        return Child.objects.select_related("family").prefetch_related(
            event_ticket_prefetch,
            session_ticket_prefetch,
        ).all()

    def perform_update(self, serializer):
        """Update last_participation_date when child info is updated"""
        serializer.save(last_participation_date=timezone.now())
