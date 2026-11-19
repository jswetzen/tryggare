"""Staff REST API for the language-model provider. The key is write-only."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LLMProvider
from .providers import ProviderError
from .services import fetch_models

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
