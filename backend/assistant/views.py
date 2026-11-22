"""Staff REST API for the language-model provider. The key is write-only."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from events import event_spec
from events.event_spec import issue
from events.models import Event
from registrations.form_spec import build_form_spec, build_form_spec_from_draft

from . import runner
from .models import AssistantConversation, LLMProvider
from .permissions import (
    EVENT_NOT_ELIGIBLE,
    NOT_AUTHENTICATED,
    PERMISSION_DENIED,
    can_use_assistant,
    fresh_user,
    lacks_permission,
)
from .providers import ProviderError
from .services import fetch_models
from feature_requests import services as feature_requests
from feature_requests.models import FeatureRequest
from feature_requests.rules import FeatureRequestError

from .tools import Drafts

logger = logging.getLogger(__name__)

VIEW_PERM = "assistant.view_llmprovider"
CHANGE_PERM = "assistant.change_llmprovider"


class CanManageProvider(BasePermission):
    """Reading needs view; writing, and loading models (it spends the key), change."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm(VIEW_PERM) or user.has_perm(CHANGE_PERM)
        return user.has_perm(CHANGE_PERM)


class ProviderSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        help_text="Blank or omitted keeps the stored key.",
    )
    clear_api_key = serializers.BooleanField(write_only=True, required=False)
    has_api_key = serializers.BooleanField(read_only=True)

    class Meta:
        model = LLMProvider
        fields = [
            "kind",
            "base_url",
            "model",
            "enabled",
            "api_key",
            "clear_api_key",
            "has_api_key",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate(self, attrs):
        instance = self.instance
        saved_base_url = instance.base_url
        key, clear = attrs.get("api_key"), attrs.get("clear_api_key")
        if key and clear:
            raise serializers.ValidationError(
                {
                    "api_key": _(
                        "Either enter a new key or remove the stored one, not both."
                    )
                }
            )
        if (
            not key
            and not clear
            and "base_url" in attrs
            and instance.key_blocked_for(attrs["base_url"], saved_base_url)
        ):
            raise serializers.ValidationError(
                {
                    "api_key": _(
                        "Enter the API key again for the new address, "
                        "or remove the stored key."
                    )
                }
            )
        for name, value in attrs.items():
            if name not in ("api_key", "clear_api_key"):
                setattr(instance, name, value)
        try:
            instance.full_clean(exclude=["updated_by"])
        except ValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from None
        return attrs

    def update(self, instance, validated_data):
        key = validated_data.pop("api_key", "")
        if validated_data.pop("clear_api_key", False):
            instance.set_api_key(None)
        elif key:
            instance.set_api_key(key)
        instance.updated_by = self.context["request"].user
        instance.save()
        return instance


class ProviderView(APIView):
    permission_classes = [CanManageProvider]
    parser_classes = [JSONParser]
    http_method_names = ["get", "head", "options", "patch"]

    def get(self, request):
        return Response(ProviderSerializer(LLMProvider.load()).data)

    def patch(self, request):
        return self._write(request)

    @transaction.atomic
    def _write(self, request):
        provider = LLMProvider.objects.select_for_update().get(pk=LLMProvider.load().pk)
        serializer = ProviderSerializer(
            provider, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProviderModelsView(APIView):
    """POST ``{"base_url"?, "api_key"?}``: the models on offer, before or after saving."""

    permission_classes = [CanManageProvider]
    parser_classes = [JSONParser]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        base_url = data.get("base_url") or ""
        api_key = data.get("api_key") or ""
        if not isinstance(base_url, str) or not isinstance(api_key, str):
            return Response(
                {"base_url": [_("Must be a string.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            models = fetch_models(LLMProvider.load(), base_url, api_key.strip())
        except ValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "error_dict")
                else {"base_url": exc.messages}
            )
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        except ProviderError as exc:
            return Response(
                {"errors": [exc.as_dict()]}, status=status.HTTP_502_BAD_GATEWAY
            )
        return Response({"models": models})


# --- the chat on the preview page; plan: "Backend modules and endpoints"


def _refusal(http_status, code, message, extra=()):
    return Response(
        {"errors": [issue("", code, message), *extra], "warnings": []},
        status=http_status,
    )


def gate(request, event_id):
    """``(user, event, None)`` or ``(None, None, refusal)``. Runs on every request,
    with a user reloaded now, in the WebSocket's order: permission is decided before
    the event is looked up, so a non-staff user cannot probe event ids."""
    user = fresh_user(request.user) if request.user.is_authenticated else None
    reason = lacks_permission(user)
    if reason == NOT_AUTHENTICATED:
        return None, None, _refusal(401, reason, _("Sign in to use the assistant."))
    if reason:
        return (
            None,
            None,
            _refusal(403, reason, _("You are not allowed to use the assistant.")),
        )
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        return None, None, _refusal(404, "event_not_found", _("No such event."))
    ok, _issues = can_use_assistant(user, event)
    if not ok:
        # The blockers keep their own codes (registration_open_on_target, event_not_empty)
        # so the page can name the reason; can_use_assistant folds them into one code.
        return (
            None,
            None,
            _refusal(
                409,
                EVENT_NOT_ELIGIBLE,
                _("The assistant cannot change this event now."),
                event_spec.apply_blockers(event),
            ),
        )
    if not LLMProvider.load().enabled:
        return (
            None,
            None,
            _refusal(503, "not_enabled", _("The assistant is not switched on.")),
        )
    return user, event, None


class AssistantAPIView(APIView):
    # Authentication is the gate's job, so it can answer 401 vs 403 as the WebSocket does.
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.user, self.event, self.refusal = gate(request, kwargs["event_id"])

    def dispatch(self, request, *args, **kwargs):
        # The SPA sends no Accept-Language, so it names the UI language (?lang=).
        lang = request.GET.get("lang")
        if lang not in dict(settings.LANGUAGES):
            lang = translation.get_language()
        with translation.override(lang):
            response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def conversation(self, create=False):
        rows = AssistantConversation.objects.filter(event=self.event, user=self.user)
        if create:
            return (
                rows.first()
                or AssistantConversation.objects.get_or_create(
                    event=self.event, user=self.user
                )[0]
            )
        return rows.first()


def is_stale(event, draft) -> bool:
    """The event's setup changed since the draft was proposed (``Drafts.is_stale``)."""
    drafts = Drafts(event)
    drafts.items[draft["token"]] = draft
    try:
        return drafts.is_stale(draft["token"])
    except event_spec.SpecError:
        return True  # the event cannot even be exported now: certainly not what the draft saw


def _no_draft():
    return _refusal(404, "no_draft", _("There is no draft."))


class ConversationView(AssistantAPIView):
    http_method_names = ["get", "head", "options", "delete"]

    def get(self, request, event_id):
        if self.refusal:
            return self.refusal
        conv = self.conversation()
        if conv is None:
            return Response(
                {
                    "available": True,
                    "conversation_id": None,
                    "transcript": [],
                    "running": False,
                    "notice_accepted": False,
                    "draft_version": 0,
                }
            )
        running = runner.reset_if_dead(conv)
        return Response(
            {
                "available": True,
                "conversation_id": str(conv.id),
                "transcript": runner.transcript(conv),
                "running": running,
                "notice_accepted": conv.notice_accepted_at is not None,
                "draft_version": conv.draft_version,
            }
        )

    def delete(self, request, event_id):
        if self.refusal:
            return self.refusal
        conv = self.conversation()
        if conv is not None:
            runner.clear_conversation(conv)
            # Only for a live run: a late cancel would hit the run the user starts
            # right after clearing (request_cancel is keyed by event and user).
            if conv.status == conv.STATUS_RUNNING:
                _tell_consumers_to_cancel(conv)
        return Response(status=204)


def _tell_consumers_to_cancel(conv) -> None:
    """A run is a task in a consumer's process and cannot be cancelled from this
    thread; the group message makes that consumer do it. Without a connected consumer
    the cleared row ends the run at its next tool call instead."""
    try:
        async_to_sync(get_channel_layer().group_send)(
            runner.group_name(conv.id), {"type": "assistant.cancel"}
        )
    except Exception as exc:
        logger.warning("assistant cancel not delivered: %s", type(exc).__name__)


class NoticeView(AssistantAPIView):
    http_method_names = ["post", "options"]

    def post(self, request, event_id):
        if self.refusal:
            return self.refusal
        conv = self.conversation(create=True)
        AssistantConversation.objects.filter(
            pk=conv.pk, notice_accepted_at__isnull=True
        ).update(notice_accepted_at=timezone.now())
        return Response({"notice_accepted": True})


class DraftView(AssistantAPIView):
    http_method_names = ["get", "head", "options", "delete"]

    def get(self, request, event_id):
        if self.refusal:
            return self.refusal
        conv = self.conversation()
        draft = conv.draft if conv else None
        if not draft:
            return _no_draft()
        return Response(
            {
                "spec": draft["spec"],
                "diff": draft.get("diff", []),
                "warnings": event_spec.localize(draft.get("warnings", [])),
                "stale": is_stale(self.event, draft),
                "token": draft.get("token"),
                "version": draft.get("version"),
            }
        )

    def delete(self, request, event_id):
        """``?version=`` is required (what ``GET`` returned; ``token`` optional): a
        discard names the draft it saw, so a newer proposal never goes with it."""
        if self.refusal:
            return self.refusal
        raw = request.query_params.get("version")
        if raw is None:
            return _refusal(400, "version_required", _("The draft version is invalid."))
        try:
            version = int(raw)
        except ValueError:
            return _refusal(400, "invalid_version", _("The draft version is invalid."))
        conv = self.conversation()
        if conv is None or not conv.draft:
            return _no_draft()
        token = request.query_params.get("token")
        if not runner.discard_draft(conv, version=version, token=token):
            conv.refresh_from_db()
            if conv.draft:
                return _refusal(
                    409,
                    "draft_changed",
                    _("The draft changed since you last saw it."),
                )
            return _no_draft()
        return Response(status=204)


class PreviewView(AssistantAPIView):
    """The register page's spec source in assistant mode: the form spec of the
    saved event, or of the event as the stored draft would leave it."""

    http_method_names = ["get", "head", "options"]

    def get(self, request, event_id):
        if self.refusal:
            return self.refusal
        conv = self.conversation()
        draft = conv.draft if conv else None
        if draft:
            try:
                form_spec, diff, warnings = build_form_spec_from_draft(
                    draft["spec"], self.event
                )
            except event_spec.SpecError:
                # The event moved on and the draft no longer applies: show what is saved.
                return Response(self._saved(stale=True, unusable=True))
            return Response(
                {
                    "source": "draft",
                    "stale": is_stale(self.event, draft),
                    "draft_unusable": False,
                    "form_spec": form_spec,
                    "diff": diff,
                    "warnings": warnings,
                }
            )
        return Response(self._saved(stale=False, unusable=False))

    def _saved(self, *, stale, unusable):
        return {
            "source": "saved",
            "stale": stale,
            "draft_unusable": unusable,
            "form_spec": build_form_spec(self.event),
            "diff": [],
            "warnings": [],
        }


# --- feature requests (review API for stage B; docs/roadmap/feature_requests.md)
# Its own gate: a draft must stay reviewable when the provider is switched off or the
# event has since acquired registrations, which the chat gate would refuse.


def feature_gate(request, event_id):
    """``(user, event, None)`` or ``(None, None, refusal)``: signed in, staff with
    event-change rights (``feature_requests.services.can_file``), and the event exists."""
    user = fresh_user(request.user) if request.user.is_authenticated else None
    if user is None:
        return (
            None,
            None,
            _refusal(401, NOT_AUTHENTICATED, _("Sign in to file a feature request.")),
        )
    if not feature_requests.can_file(user):
        return (
            None,
            None,
            _refusal(
                403,
                PERMISSION_DENIED,
                _("You are not allowed to file feature requests."),
            ),
        )
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        return None, None, _refusal(404, "event_not_found", _("No such event."))
    return user, event, None


class FeatureRequestAPIView(AssistantAPIView):
    def initial(self, request, *args, **kwargs):
        APIView.initial(self, request, *args, **kwargs)  # not the chat gate
        self.user, self.event, self.refusal = feature_gate(request, kwargs["event_id"])

    def own_draft(self, request_id):
        """This user's draft on this event, or None (another organizer's id reads as absent)."""
        digits = request_id[3:] if request_id.startswith("FR-") else ""
        if not digits.isdigit():
            return None
        return FeatureRequest.objects.filter(
            pk=int(digits), event=self.event, filed_by=self.user, status="draft"
        ).first()

    def feature_errors(self, exc):
        return Response({"errors": exc.errors, "warnings": []}, status=400)


class FeatureRequestListView(FeatureRequestAPIView):
    """GET: this user's drafts on the event. POST: file one yourself (source organizer)."""

    http_method_names = ["get", "head", "options", "post"]

    def get(self, request, event_id):
        if self.refusal:
            return self.refusal
        rows = feature_requests.drafts_for(self.event, self.user)
        return Response({"drafts": [feature_requests.serialize(r) for r in rows]})

    def post(self, request, event_id):
        if self.refusal:
            return self.refusal
        if not isinstance(request.data, dict):
            return _refusal(400, "invalid", _("Must be a JSON object."))
        try:
            row, _match = feature_requests.file_draft(
                self.event, self.user, request.data, source="organizer"
            )
        except FeatureRequestError as exc:
            return self.feature_errors(exc)
        return Response(feature_requests.serialize(row), status=201)


class FeatureRequestConfirmView(FeatureRequestAPIView):
    """POST, optionally with edited fields: the whole input is checked again. Joins an
    open request with the same key when there is one (seen goes up)."""

    http_method_names = ["post", "options"]

    def post(self, request, event_id, request_id):
        if self.refusal:
            return self.refusal
        row = self.own_draft(request_id)
        if row is None:
            return _no_draft()
        if request.data and not isinstance(request.data, dict):
            return _refusal(400, "invalid", _("Must be a JSON object."))
        try:
            row = feature_requests.confirm(row, self.user, request.data or None)
        except FeatureRequestError as exc:
            return self.feature_errors(exc)
        return Response(
            {
                "id": row.public_id,
                "status": row.status,
                "duplicate_of": row.duplicate_of.public_id
                if row.duplicate_of_id
                else None,
            }
        )


class FeatureRequestDiscardView(FeatureRequestAPIView):
    http_method_names = ["post", "options"]

    def post(self, request, event_id, request_id):
        if self.refusal:
            return self.refusal
        row = self.own_draft(request_id)
        if row is None:
            return _no_draft()
        feature_requests.discard(row)
        return Response(status=204)
