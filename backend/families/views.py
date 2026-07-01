from django.db.models import Prefetch
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from events.models import EventTicket, SessionTicket
from .dsar import (
    build_family_export,
    family_export_to_csv,
    scrub_audit_logs_for_children,
)
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
            "children__event_tickets",
            queryset=EventTicket.objects.select_related("event"),
        )
        session_ticket_prefetch = Prefetch(
            "children__session_tickets",
            queryset=SessionTicket.objects.select_related("session", "session__event"),
        )
        # Prefetch active check-ins for children to avoid N+1 queries
        active_checkins_prefetch = Prefetch(
            "children__checkin_records",
            queryset=CheckInRecord.objects.filter(check_out_time__isnull=True),
            to_attr="active_checkins",
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

    def retrieve(self, request, *args, **kwargs):
        """Full family detail includes allergies/notes — log the access."""
        from checkins.audit import log_audit

        response = super().retrieve(request, *args, **kwargs)
        log_audit(
            request,
            action="record_viewed",
            entity_type="Family",
            entity_id=kwargs.get("pk", ""),
        )
        return response

    @action(detail=False, methods=["get"], url_path="by-ticket")
    def ticket_lookup(self, request):
        code = request.query_params.get("code", "").strip()
        if not code:
            return Response({"error": "code required"}, status=400)

        family = None
        ticket = (
            EventTicket.objects.filter(external_ticket_code=code)
            .select_related("child__family")
            .first()
        )
        if ticket:
            family = ticket.child.family
        else:
            ticket = (
                SessionTicket.objects.filter(external_ticket_code=code)
                .select_related("child__family")
                .first()
            )
            if ticket:
                family = ticket.child.family

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

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """
        GDPR right-to-access / portability: export everything held about this
        family (parents, children, check-in history, audit trail).

        Returns JSON by default, or CSV with ``?as=csv``. (We avoid the ``format``
        query param because DRF reserves it for content-negotiation suffixes.)
        """
        from checkins.audit import log_audit

        family = self.get_object()
        data = build_family_export(family)
        export_as = request.query_params.get("as", "json")

        log_audit(
            request,
            action="dsar_export",
            entity_type="Family",
            entity_id=str(family.id),
            details={"format": export_as},
        )

        if export_as == "csv":
            response = HttpResponse(family_export_to_csv(data), content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="family-{family.id}.csv"'
            )
            return response

        return Response(data)

    @action(detail=True, methods=["post"])
    def erase(self, request, pk=None):
        """
        GDPR right-to-erasure: export the family's data, scrub its children's
        audit-log PII, then hard-delete the family (cascades to parents,
        children and their check-in records).

        The export is returned in the response so the operator retains a copy,
        and an audit entry is written *before* deletion so the action is logged.
        """
        from checkins.audit import log_audit

        family = self.get_object()
        export = build_family_export(family)
        child_ids = [str(c.id) for c in family.children.all()]

        log_audit(
            request,
            action="dsar_erasure",
            entity_type="Family",
            entity_id=str(family.id),
            details={
                "last_name": family.last_name,
                "child_count": len(child_ids),
            },
        )
        scrub_audit_logs_for_children(child_ids)
        family.delete()

        return Response({"erased": True, "export": export})


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
