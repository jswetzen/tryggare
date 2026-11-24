"""Staff REST API for the event spec; the logic lives in ``events.event_spec``."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.parsers import JSONParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import event_spec
from .event_spec import issue
from .models import Event
from .services import COPY_PERMISSIONS, REPLACE_PERMISSIONS, VIEW_PERMISSIONS

# Refusals that describe the target's state, not the spec: 409 on PUT.
_CONFLICT_CODES = {
    "event_not_empty",
    "registration_open_on_target",
    "cross_event_reference",
}


class CanManageEventSpecs(BasePermission):
    """Per method, from ``view.permissions_by_method``: creating needs the copy
    action's permissions, replacing also change and delete, reading view on every
    spec model (an export includes promo codes)."""

    def has_permission(self, request, view):
        needed = view.permissions_by_method.get(request.method)
        user = request.user
        return bool(
            needed is not None
            and user
            and user.is_authenticated
            and all(user.has_perm(p) for p in needed)
        )


def _errors(status_code, *issues, warnings=()):
    return Response(
        {"errors": list(issues), "warnings": list(warnings)}, status=status_code
    )


def _body(request):
    """The JSON object body, or a 400 Response in the same shape as other errors."""
    try:
        data = request.data
    except (ParseError, UnsupportedMediaType):
        return None, _errors(
            400, issue("", "malformed_body", _("The body is not valid JSON."))
        )
    if not isinstance(data, dict):
        return None, _errors(
            400, issue("", "malformed_body", _("The body must be a JSON object."))
        )
    return data, None


def _spec_body(request):
    """``{"spec": {...}}``, or the spec itself so an export can be sent straight back."""
    data, error = _body(request)
    if error:
        return None, error
    if "event_spec_version" in data:
        return data, None
    if not isinstance(data.get("spec"), dict):
        return None, _errors(
            400, issue("spec", "spec_missing", _("The body needs a 'spec' object."))
        )
    return data["spec"], None


def _not_found():
    return _errors(404, issue("event", "event_not_found"))


def _event_or_404(event_id):
    try:
        event = Event.objects.filter(pk=event_id).first()
    except (ValidationError, ValueError):
        event = None
    return (event, None) if event else (None, _not_found())


class SpecAPIView(APIView):
    permission_classes = [CanManageEventSpecs]
    parser_classes = [JSONParser]
    permissions_by_method = {m: VIEW_PERMISSIONS for m in ("GET", "HEAD", "OPTIONS")}

    def handle_exception(self, exc):
        """Give 403, 404, 429 and the rest the same error shape as our own."""
        response = super().handle_exception(exc)
        detail = getattr(response, "data", None)
        if (
            response.status_code >= 400
            and isinstance(detail, dict)
            and "detail" in detail
        ):
            code = getattr(detail["detail"], "code", "error")
            response.data = {
                "errors": [issue("", code, detail["detail"])],
                "warnings": [],
            }
        return response


class SchemaView(SpecAPIView):
    def get(self, request):
        return Response(
            {
                "schema": event_spec.JSON_SCHEMA,
                "capabilities": event_spec.CAPABILITIES,
                "example": event_spec.example_spec(),
            }
        )


class ValidateView(SpecAPIView):
    permissions_by_method = {"POST": VIEW_PERMISSIONS}

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
                return _errors(
                    400,
                    issue(
                        "event_id",
                        "invalid_event_id",
                        _("'event_id' is not a valid id."),
                    ),
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
        codes = {e["code"] for e in exc.errors}
        if "event_not_found" in codes:
            return _not_found()
        conflict = bool(codes & _CONFLICT_CODES) and success_status == 200
        return _errors(409 if conflict else 400, *exc.errors, warnings=exc.warnings)
    return Response(
        {"event_id": str(event.pk), "diff": changes, "warnings": warnings},
        status=success_status,
    )


class CreateView(SpecAPIView):
    permissions_by_method = {"POST": COPY_PERMISSIONS}

    def post(self, request):
        spec, error = _spec_body(request)
        if error:
            return error
        return _apply(spec, None, 201)


class EventSpecView(SpecAPIView):
    permissions_by_method = {
        "GET": VIEW_PERMISSIONS,
        "HEAD": VIEW_PERMISSIONS,
        "PUT": REPLACE_PERMISSIONS,
    }

    def get(self, request, event_id):
        event, error = _event_or_404(event_id)
        if error:
            return error
        try:
            return Response(event_spec.export(event))
        except event_spec.SpecError as exc:
            return _errors(409, *exc.errors)

    def put(self, request, event_id):
        spec, error = _spec_body(request)
        if error:
            return error
        event, error = _event_or_404(event_id)
        if error:
            return error
        # Imported here: assistant imports events. The assistant's draft is applied
        # through this endpoint, and an applied draft cannot be rolled back.
        from assistant.runner import run_in_progress

        if run_in_progress(event, request.user):
            return _errors(
                409,
                issue(
                    "",
                    "run_in_progress",
                    _("Wait for the assistant to finish its reply."),
                ),
            )
        return _apply(spec, event, 200)


class EventSpecDiffView(SpecAPIView):
    permissions_by_method = {"POST": VIEW_PERMISSIONS}

    def post(self, request, event_id):
        spec, error = _spec_body(request)
        if error:
            return error
        event, error = _event_or_404(event_id)
        if error:
            return error
        return Response(event_spec.check(spec, event))
