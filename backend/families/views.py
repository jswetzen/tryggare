from django.db.models import Prefetch
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import DjangoModelPermissionsWithView, model_permissions

from events.models import EventTicket, SessionTicket
from registrations.models import Registration
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
    FamilyUpdateSerializer,
    ParentSerializer,
)


class FamilyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing families.

    Gated on the matching ``families`` model permission. The two GDPR actions
    (``export``/``erase``) are gated on their own permissions instead — see
    ``get_permissions`` below.
    """

    permission_classes = [DjangoModelPermissionsWithView]

    # DSAR export is a GET and erasure is a POST, so the default verb mapping
    # would gate them on ``view_family`` and ``add_family`` respectively — the
    # first is the permission that opens the check-in screen's family lookup,
    # the second reads as harmless and hard-deletes a family. Both get a
    # purpose-named permission of their own (families/models.py Meta).
    _dsar_export_permission = model_permissions(
        Family,
        perms_map={"GET": ["%(app_label)s.export_family_dsar"]},
        name="DsarExportPermissions",
    )
    _dsar_erase_permission = model_permissions(
        Family,
        perms_map={"POST": ["%(app_label)s.erase_family_dsar"]},
        name="DsarErasePermissions",
    )

    # Revealing safety info is a POST that reads. The default map would gate it
    # on ``add_family`` — the permission that creates a household — which no
    # Volontär holds and which is not what this action does. It requires no
    # more than the read that already put the family on their screen; the
    # per-attendee check lives in the action itself.
    _reveal_safety_info_permission = model_permissions(
        Family,
        perms_map={"POST": ["%(app_label)s.view_%(model_name)s"]},
        name="SafetyInfoRevealPermissions",
    )

    def get_permissions(self):
        if self.action == "export":
            return [self._dsar_export_permission()]
        if self.action == "erase":
            return [self._dsar_erase_permission()]
        if self.action == "reveal_safety_info":
            return [self._reveal_safety_info_permission()]
        return super().get_permissions()

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

        # 9.3 "unpaid at the door": the check-in family list needs to know
        # which families have a pending_payment registration, and for how
        # much, without an N+1 per family — prefetched once here rather
        # than resolved in the serializer.
        pending_payment_qs = Registration.objects.filter(
            status=Registration.Status.PENDING_PAYMENT
        ).select_related("payment")

        return Family.objects.prefetch_related(
            Prefetch("attendees", queryset=children_qs, to_attr="children"),
            Prefetch("attendees", queryset=parents_qs, to_attr="parents"),
            Prefetch(
                "registrations",
                queryset=pending_payment_qs,
                to_attr="pending_payment_registrations",
            ),
        ).all()

    def get_serializer_class(self):
        if self.action == "create":
            return FamilyCreateSerializer
        if self.action in ("update", "partial_update"):
            return FamilyUpdateSerializer
        if self.action == "retrieve":
            return FamilyDetailSerializer
        return FamilySerializer

    def update(self, request, *args, **kwargs):
        """FamilyUpdateSerializer is input-only — its nested upsert
        serializers don't carry the ticket/check-in fields the check-in UI
        needs back. Re-fetch through the fully-prefetched queryset and
        reserialize with FamilyDetailSerializer for the response, the same
        shape retrieve() already returns."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        family = serializer.save()
        output = FamilyDetailSerializer(
            self.get_queryset().get(pk=family.pk),
            context=self.get_serializer_context(),
        )
        return Response(output.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

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
        # Context matters: without the request, SafetyInfoDisclosureMixin has
        # no user to ask and masks the health text for everyone, including the
        # roles that may edit it.
        serializer = ChildSerializer(
            children, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def parents(self, request, pk=None):
        """Get all parents for a specific family"""
        family = self.get_object()
        parents = family.parents.all()
        serializer = ParentSerializer(
            parents, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="reveal-safety-info")
    def reveal_safety_info(self, request, pk=None):
        """Disclose one attendee's allergy/emergency-medical text, and log it.

        The check-in path's counterpart to ``qr_reveal_safety_info``. The door
        volunteer is the person who most needs to know about a peanut allergy,
        so this is reveal-with-audit rather than hidden: the roster says *there
        is safety info here* (``has_safety_info``) and this endpoint hands over
        the text, writing exactly one ``safety_info_revealed`` row per call.
        Distinct from the ``record_viewed`` row ``retrieve`` writes, so opening
        a family stays distinguishable from reading a child's allergy — the
        same granularity the QR path already has, which is the point: an audit
        trail with one careful half and one silent half is not an audit trail.

        Body: ``{"attendee_id": "<uuid>"}`` — a Child *or* a Parent of this
        family. Adults carry these fields too and their allergy is no less
        special-category, so the endpoint is attendee-shaped, not child-shaped.

        Authorisation: reaching a family at all is ``families.view_family``
        (below), and the per-attendee ``view_child``/``view_parent`` check
        happens once the type is known. Deliberately *not* gated on
        ``change_*``: a holder of that already receives the text unrevealed
        (see SafetyInfoDisclosureMixin), so gating on it here would leave the
        endpoint reachable by exactly the people who never need it.
        """
        from checkins.audit import log_audit

        family = self.get_object()
        attendee_id = str(request.data.get("attendee_id") or "").strip()
        if not attendee_id:
            return Response({"error": "attendee_id required"}, status=400)

        attendee = Child.objects.filter(pk=attendee_id, family=family).first()
        entity_type = "Child"
        required_permission = "families.view_child"
        if attendee is None:
            attendee = Parent.objects.filter(pk=attendee_id, family=family).first()
            entity_type = "Parent"
            required_permission = "families.view_parent"

        if attendee is None:
            # Scoped to this family on purpose: the family is the object the
            # caller was already authorised for, so an unrelated attendee id
            # must not become readable by pairing it with a family they can see.
            return Response({"error": "not_found"}, status=404)

        if not request.user.has_perm(required_permission):
            return Response({"error": "forbidden"}, status=403)

        allergies = attendee.allergies or ""
        notes = attendee.notes or ""

        log_audit(
            request,
            action="safety_info_revealed",
            entity_type=entity_type,
            entity_id=str(attendee.id),
            details={
                "family_id": str(family.id),
                "had_allergies": bool(allergies),
                "had_notes": bool(notes),
            },
        )

        return Response({"allergies": allergies, "notes": notes})

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
                "child_count": len(child_ids),
            },
        )
        scrub_audit_logs_for_children(child_ids)
        family.delete()

        return Response({"erased": True, "export": export})


class ParentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing parents.
    Gated on the matching ``families.*_parent`` permission.
    """

    queryset = Parent.objects.select_related("family").all()
    serializer_class = ParentSerializer
    permission_classes = [DjangoModelPermissionsWithView]
    search_fields = ["first_name", "last_name", "email", "phone"]
    filterset_fields = ["family", "relationship_type"]


class ChildViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing children.
    Gated on the matching ``families.*_child`` permission.
    """

    serializer_class = ChildSerializer
    permission_classes = [DjangoModelPermissionsWithView]
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
