from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from checkins.audit import log_audit
from checkins.eligibility import (
    GRANT_ALREADY_TICKETED,
    door_grant_error,
    registration_cancelled_refusal,
)
from config.permissions import (
    POST_REQUIRES_CHANGE,
    DjangoModelPermissionsWithView,
    model_permissions,
)

from .models import Event, EventTicket, Session, SessionTicket, Ticket
from .serializers import (
    EventSerializer,
    DoorGrantSerializer,
    EventTicketSerializer,
    SessionSerializer,
    SessionTicketSerializer,
    TicketSerializer,
)


def _refusal(code: str, message: str) -> Response:
    return Response(
        {"error": message, "code": code}, status=status.HTTP_400_BAD_REQUEST
    )


def _door_grant(request, model, lookup, serializer_class, entity_type, action):
    """Shared body of both ``grant/`` actions.

    The client names only the person and the session it is checking them into;
    the event is derived from that session, never taken from the request. One
    ``AuditLog`` row per grant, written in the same transaction as the ticket.
    """
    body = DoorGrantSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    attendee = body.validated_data["attendee"]
    session = body.validated_data["session"]

    refusal = door_grant_error(attendee, session)
    if refusal:
        return _refusal(*refusal)

    existing = (
        model.objects.filter(attendee=attendee, **lookup(session))
        .select_related("registration")
        .first()
    )
    if existing is not None:
        return _existing_ticket_refusal(existing)

    try:
        with transaction.atomic():
            ticket = model.objects.create(attendee=attendee, **lookup(session))
            log_audit(
                request,
                action=action,
                entity_type=entity_type,
                entity_id=str(ticket.id),
                details={
                    "attendee_id": str(attendee.id),
                    "attendee_name": f"{attendee.first_name} {attendee.last_name}",
                    "session_id": str(session.id),
                    "session_name": session.name,
                    "event_id": str(session.event_id),
                    "event_name": session.event.name,
                    "granted_by": request.user.get_username(),
                },
            )
    except IntegrityError:
        # Lost a race with another desk granting the same ticket.
        return _refusal(
            GRANT_ALREADY_TICKETED, _("This person already has a ticket here")
        )
    return Response(serializer_class(ticket).data, status=status.HTTP_201_CREATED)


def _existing_ticket_refusal(ticket) -> Response:
    from registrations.models import Registration

    if (
        ticket.registration_id
        and ticket.registration.status == Registration.Status.CANCELLED
    ):
        # Spec: a cancelled registration's ticket stays refused at the door;
        # only a Koordinator may sort it out.
        return _refusal(*registration_cancelled_refusal())
    return _refusal(GRANT_ALREADY_TICKETED, _("This person already has a ticket here"))


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
    # `ticket_rule` is the session's OWN value: blank means "inherits the
    # event default", it does not match the effective rule. (The old
    # `requires_ticket` filter had no frontend caller and was dropped.)
    filterset_fields = ["event", "is_active", "ticket_rule"]
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

    # The check-in desk's one-tap grant. Its own route and its own permission
    # (``events.grant_eventticket_at_door``)
    # rather than the viewset's ``add_`` mapping, so that a Volontär
    # can admit a ticketless child or adult at the door without holding
    # ``add_eventticket`` (which opens the Django-admin add form and the
    # general ``POST`` on this viewset, and is ticket administration).
    # It creates exactly what the general ``POST`` would -- same serializer,
    # same validation -- and nothing else is reachable through it: no update,
    # no delete, no ticket-type or price fields (the serializer exposes none).
    @action(
        detail=False,
        methods=["post"],
        url_path="grant",
        permission_classes=[
            model_permissions(
                EventTicket,
                perms_map={"POST": ["events.grant_eventticket_at_door"]},
                name="EventTicketGrantAtDoorPermission",
            )
        ],
    )
    def grant(self, request):
        return _door_grant(
            request,
            EventTicket,
            lambda session: {"event": session.event},
            EventTicketSerializer,
            "EventTicket",
            "ticket_granted_at_door",
        )


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

    # The check-in desk's one-tap grant. Its own route and its own permission
    # (``events.grant_sessionticket_at_door``)
    # rather than the viewset's ``add_`` mapping, so that a Volontär
    # can admit a ticketless child or adult at the door without holding
    # ``add_sessionticket`` (which opens the Django-admin add form and the
    # general ``POST`` on this viewset, and is ticket administration).
    # It creates exactly what the general ``POST`` would -- same serializer,
    # same validation -- and nothing else is reachable through it: no update,
    # no delete, no ticket-type or price fields (the serializer exposes none).
    @action(
        detail=False,
        methods=["post"],
        url_path="grant",
        permission_classes=[
            model_permissions(
                SessionTicket,
                perms_map={"POST": ["events.grant_sessionticket_at_door"]},
                name="SessionTicketGrantAtDoorPermission",
            )
        ],
    )
    def grant(self, request):
        return _door_grant(
            request,
            SessionTicket,
            lambda session: {"session": session},
            SessionTicketSerializer,
            "SessionTicket",
            "ticket_granted_at_door",
        )
