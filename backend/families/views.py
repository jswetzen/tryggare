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
        Includes ticket information and check-in status for children and parents.

        Since Child and Parent are MTI subclasses of Attendee, their family FK
        lives on the Attendee table. We prefetch through "attendees" and store
        each subclass in a to_attr that Family._AttendeeSubclassAccessor exposes.
        """
        from checkins.models import CheckInRecord

        # Prefetch children with their tickets and active check-ins
        children_qs = Child.objects.prefetch_related(
            Prefetch(
                "event_tickets",
                queryset=EventTicket.objects.select_related("event"),
            ),
            Prefetch(
                "session_tickets",
                queryset=SessionTicket.objects.select_related(
                    "session", "session__event"
                ),
            ),
            Prefetch(
                "checkin_records",
                queryset=CheckInRecord.objects.filter(check_out_time__isnull=True),
                to_attr="active_checkins",
            ),
        )

        # Prefetch parents with their tickets and active check-ins
        parents_qs = Parent.objects.prefetch_related(
            Prefetch(
                "event_tickets",
                queryset=EventTicket.objects.select_related("event"),
            ),
            Prefetch(
                "session_tickets",
                queryset=SessionTicket.objects.select_related(
                    "session", "session__event"
                ),
            ),
            Prefetch(
                "checkin_records",
                queryset=CheckInRecord.objects.filter(check_out_time__isnull=True),
                to_attr="active_checkins",
            ),
        )

        return Family.objects.prefetch_related(
            Prefetch("attendees", queryset=children_qs, to_attr="children"),
            Prefetch("attendees", queryset=parents_qs, to_attr="parents"),
        ).all()

    def get_serializer_class(self):
        if self.action == "create":
            return FamilyCreateSerializer
        if self.action == "retrieve":
            return FamilyDetailSerializer
        return FamilySerializer

    @action(detail=False, methods=["get"], url_path="by-ticket")
    def ticket_lookup(self, request):
        code = request.query_params.get("code", "").strip()
        if not code:
            return Response({"error": "code required"}, status=400)

        family = None
        ticket = (
            EventTicket.objects.filter(external_ticket_code=code)
            .select_related("attendee__family")
            .first()
        )
        if ticket:
            family = ticket.attendee.family
        else:
            ticket = (
                SessionTicket.objects.filter(external_ticket_code=code)
                .select_related("attendee__family")
                .first()
            )
            if ticket:
                family = ticket.attendee.family

        if not family:
            return Response({"error": "not_found"}, status=404)

        # Use the full queryset to get the family with all prefetches
        family_qs = self.get_queryset().filter(pk=family.pk).first()
        if not family_qs:
            return Response({"error": "not_found"}, status=404)

        serializer = self.get_serializer(family_qs)
        return Response(serializer.data)

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
    search_fields = ["first_name", "last_name", "email", "phone"]
    filterset_fields = ["family", "relationship_type"]


class ChildViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing children.
    Requires authentication for most actions.
    """

    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name"]
    filterset_fields = ["family"]

    def get_queryset(self):
        """
        Optimize queries with select_related and prefetch_related.
        Includes ticket information and check-in status to avoid N+1 queries.
        """
        from checkins.models import CheckInRecord

        event_ticket_prefetch = Prefetch(
            "event_tickets", queryset=EventTicket.objects.select_related("event")
        )
        session_ticket_prefetch = Prefetch(
            "session_tickets",
            queryset=SessionTicket.objects.select_related("session", "session__event"),
        )
        # Prefetch all check-in records to avoid N+1 queries when checking is_checked_in
        # We prefetch all records (not just active ones) so the relationship name stays the same
        checkin_prefetch = Prefetch(
            "checkin_records", queryset=CheckInRecord.objects.all()
        )

        return (
            Child.objects.select_related("family")
            .prefetch_related(
                event_ticket_prefetch,
                session_ticket_prefetch,
                checkin_prefetch,
            )
            .all()
        )

    def perform_update(self, serializer):
        """Update last_participation_date when child info is updated"""
        serializer.save(last_participation_date=timezone.now())
