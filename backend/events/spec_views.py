"""Staff REST API for the event spec; the logic lives in ``events.event_spec``."""

from uuid import UUID

from django.utils.translation import gettext as _
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.parsers import JSONParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import event_spec
from .models import Event
from .services import can_copy_events

# Refusals that describe the target's state, not the spec: 409 on PUT.
_CONFLICT_CODES = {"event_not_empty", "registration_open_on_target"}


class CanManageEventSpecs(BasePermission):
    """Same rule as the copy-event admin action."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and can_copy_events(user))


def _issue(path, code, message):
    return {"path": path, "code": code, "message": str(message)}


def _bad_request(path, code, message):
    return Response(
        {"errors": [_issue(path, code, message)], "warnings": []},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _body(request):
    """The JSON object body, or a 400 Response in the same shape as other errors."""
    try:
        data = request.data
    except (ParseError, UnsupportedMediaType):
        return None, _bad_request(
            "", "malformed_body", _("The body is not valid JSON.")
        )
    if not isinstance(data, dict):
        return None, _bad_request(
            "", "malformed_body", _("The body must be a JSON object.")
        )
    return data, None


def _spec_body(request):
    data, error = _body(request)
    if error:
        return None, error
    if not isinstance(data.get("spec"), dict):
        return None, _bad_request(
            "spec", "spec_missing", _("The body needs a 'spec' object.")
        )
    return data["spec"], None


def _event_or_404(event_id):
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        return None, Response(
            {
                "errors": [
                    _issue("event", "event_not_found", _("The event does not exist."))
                ],
                "warnings": [],
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    return event, None


class SpecAPIView(APIView):
    permission_classes = [CanManageEventSpecs]
    parser_classes = [JSONParser]


class SchemaView(SpecAPIView):
    def get(self, request):
        return Response(
            {
                "schema": event_spec.json_schema(),
                "capabilities": event_spec.capabilities(),
                "example": event_spec.example_spec(),
            }
        )


class ValidateView(SpecAPIView):
    def post(self, request):
        spec, error = _spec_body(request)
        if error:
            return error
        event = None
        event_id = request.data.get("event_id")
        if event_id is not None:
            try:
                event_id = UUID(str(event_id))
            except ValueError:
                return _bad_request(
                    "event_id", "invalid_event_id", _("'event_id' is not a valid id.")
                )
            event, error = _event_or_404(event_id)
            if error:
                return error
        errors, warnings = event_spec.validate(spec, event)
        return Response({"valid": not errors, "errors": errors, "warnings": warnings})


def _apply(spec, event, success_status):
    try:
        event, changes, warnings = event_spec.apply(spec, event)
    except event_spec.SpecError as exc:
        conflict = any(e["code"] in _CONFLICT_CODES for e in exc.errors)
        return Response(
            {"errors": exc.errors, "warnings": exc.warnings},
            status=(
                status.HTTP_409_CONFLICT
                if conflict and success_status == status.HTTP_200_OK
                else status.HTTP_400_BAD_REQUEST
            ),
        )
    return Response(
        {"event_id": str(event.pk), "diff": changes, "warnings": warnings},
        status=success_status,
    )


class CreateView(SpecAPIView):
    def post(self, request):
        spec, error = _spec_body(request)
        if error:
            return error
        return _apply(spec, None, status.HTTP_201_CREATED)


class EventSpecView(SpecAPIView):
    def get(self, request, event_id):
        event, error = _event_or_404(event_id)
        if error:
            return error
        try:
            return Response(event_spec.export(event))
        except ValueError as exc:
            return Response(
                {
                    "errors": [_issue("event", "cross_event_reference", str(exc))],
                    "warnings": [],
                },
                status=status.HTTP_409_CONFLICT,
            )

    def put(self, request, event_id):
        spec, error = _spec_body(request)
        if error:
            return error
        event, error = _event_or_404(event_id)
        if error:
            return error
        return _apply(spec, event, status.HTTP_200_OK)


class EventSpecDiffView(SpecAPIView):
    def post(self, request, event_id):
        spec, error = _spec_body(request)
        if error:
            return error
        event, error = _event_or_404(event_id)
        if error:
            return error
        errors, warnings = event_spec.validate(spec, event)
        try:
            changes = event_spec.diff(event, spec)
        except PydanticValidationError:
            changes = []  # wrong shape: the errors above say where
        except ValueError as exc:
            changes = []
            errors.append(_issue("event", "cross_event_reference", str(exc)))
        return Response({"diff": changes, "errors": errors, "warnings": warnings})
