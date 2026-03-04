import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from events.models import Event

from .importer import ProviderFetchError, ProviderLoginError, fetch_from_provider, run_import
from .models import EventImportConfig, ImportProvider, ImportRun
from .parser import discover_child_prefixes, parse_json_with_duplicate_keys
from .serializers import (
    EventImportConfigSerializer,
    ImportProviderSerializer,
    ImportRunListSerializer,
    ImportRunSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def discover_prefixes_view(request):
    """
    POST /api/imports/discover-prefixes/
    Body: {"json_string": "..."} (raw JSON text)

    Scans all bookings in the uploaded JSON and returns discovered child
    ticket prefixes with sample children and booking counts.

    Accepts raw JSON string to preserve duplicate keys that the external
    booking system emits (e.g. multiple standalone "Ålder" keys).
    """
    json_string = request.data.get("json_string")
    if not isinstance(json_string, str):
        return Response(
            {"detail": "json_string must be a JSON string."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        json_data = parse_json_with_duplicate_keys(json_string)
    except (ValueError, TypeError) as exc:
        return Response(
            {"detail": f"Invalid JSON: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(json_data, dict):
        return Response(
            {"detail": "JSON must be an object at the top level."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prefixes = discover_child_prefixes(json_data)
    total_bookings = sum(
        1 for v in json_data.values() if isinstance(v, dict)
    )

    return Response(
        {
            "prefixes": prefixes,
            "total_bookings": total_bookings,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_import_config(request, event_id):
    """
    GET /api/imports/events/<event_id>/config/

    Returns the saved EventImportConfig for this event, or 404 if none exists.
    """
    event = get_object_or_404(Event, pk=event_id)
    config = EventImportConfig.objects.filter(event=event).first()
    if config is None:
        return Response({"detail": "No import config for this event."}, status=status.HTTP_404_NOT_FOUND)
    return Response(EventImportConfigSerializer(config).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_import_view(request, event_id):
    """
    POST /api/imports/events/<event_id>/run/

    Two modes:
    1. Manual file upload:
       Body: {"json_string": "...", "field_mappings": {...}, "source_file_name": "..."}
    2. Auto-fetch from provider (json_string omitted):
       Body: {"field_mappings": {...}}
       Requires EventImportConfig with a linked provider that has credentials.

    Creates or updates EventImportConfig (field_mappings only), runs import synchronously,
    returns the ImportRun with full results.
    """
    event = get_object_or_404(Event, pk=event_id)

    json_string = request.data.get("json_string")
    field_mappings = request.data.get("field_mappings")

    if json_string is not None:
        # ── Manual file path ──────────────────────────────────────────────────
        if not isinstance(json_string, str):
            return Response(
                {"detail": "json_string must be a JSON string."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            json_data = parse_json_with_duplicate_keys(json_string)
        except (ValueError, TypeError) as exc:
            return Response(
                {"detail": f"Invalid JSON: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(json_data, dict):
            return Response(
                {"detail": "JSON must be an object at the top level."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(field_mappings, dict):
            return Response(
                {"detail": "field_mappings must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        source_file_name = str(request.data.get("source_file_name", "")).strip()

    else:
        # ── Auto-fetch path ───────────────────────────────────────────────────
        if not isinstance(field_mappings, dict):
            return Response(
                {"detail": "field_mappings must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config_qs = EventImportConfig.objects.filter(event=event).select_related("provider")
        config_obj = config_qs.first()
        if config_obj is None or config_obj.provider is None:
            return Response(
                {"detail": "No import provider configured for this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider = config_obj.provider
        if not provider.has_credentials:
            return Response(
                {"detail": "Provider has no credentials stored."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            raw_text = fetch_from_provider(provider)
        except ProviderLoginError as exc:
            logger.warning("Provider login error for event %s: %s", event_id, exc)
            return Response(
                {"detail": f"Provider login failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ProviderFetchError as exc:
            logger.warning("Provider fetch error for event %s: %s", event_id, exc)
            return Response(
                {"detail": f"Provider fetch failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            json_data = parse_json_with_duplicate_keys(raw_text)
        except (ValueError, TypeError) as exc:
            return Response(
                {"detail": f"Provider returned invalid JSON: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not isinstance(json_data, dict):
            return Response(
                {"detail": "Provider JSON must be an object at the top level."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        source_file_name = f"auto-fetch:{provider.name}"

    # Create or update the config (field_mappings only; provider FK is not touched here)
    config, _ = EventImportConfig.objects.get_or_create(event=event)
    config.field_mappings = field_mappings
    config.save(update_fields=["field_mappings", "updated_at"])

    # Run the import synchronously
    try:
        import_run = run_import(json_data, config, request.user)
        import_run.source_file_name = source_file_name
        import_run.save(update_fields=["source_file_name"])
    except Exception as exc:
        logger.exception("Unhandled error during import for event %s", event_id)
        return Response(
            {"detail": f"Import failed: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(ImportRunSerializer(import_run).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_history(request, event_id):
    """
    GET /api/imports/events/<event_id>/history/

    Returns ImportRun list for this event's config, newest first.
    """
    event = get_object_or_404(Event, pk=event_id)
    config = EventImportConfig.objects.filter(event=event).first()
    if config is None:
        return Response([])

    runs = ImportRun.objects.filter(config=config).order_by("-started_at")
    return Response(ImportRunListSerializer(runs, many=True).data)


# ── Provider CRUD ─────────────────────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def list_create_provider_view(request):
    """GET /api/imports/providers/ or POST /api/imports/providers/"""
    if request.method == "GET":
        providers = ImportProvider.objects.all()
        return Response(ImportProviderSerializer(providers, many=True).data)
    serializer = ImportProviderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    provider = serializer.save()
    return Response(ImportProviderSerializer(provider).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def provider_detail_view(request, provider_id):
    """GET/PUT/DELETE /api/imports/providers/<provider_id>/"""
    provider = get_object_or_404(ImportProvider, pk=provider_id)
    if request.method == "GET":
        return Response(ImportProviderSerializer(provider).data)
    if request.method == "PUT":
        serializer = ImportProviderSerializer(provider, data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(ImportProviderSerializer(serializer.save()).data)
    provider.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def set_config_provider_view(request, event_id):
    """PATCH /api/imports/events/<event_id>/config/provider/"""
    event = get_object_or_404(Event, pk=event_id)
    config, _ = EventImportConfig.objects.get_or_create(event=event)
    provider_id = request.data.get("provider_id")
    config.provider = get_object_or_404(ImportProvider, pk=provider_id) if provider_id else None
    config.save(update_fields=["provider"])
    return Response(EventImportConfigSerializer(config).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def discover_prefixes_from_provider_view(request, event_id):
    """
    POST /api/imports/events/<event_id>/discover-prefixes/

    Fetches data from the event's linked provider and runs discover_child_prefixes.
    Returns {prefixes, total_bookings} — same shape as the top-level discover-prefixes endpoint.
    """
    event = get_object_or_404(Event, pk=event_id)
    config = EventImportConfig.objects.filter(event=event).select_related("provider").first()
    if config is None or config.provider is None:
        return Response(
            {"detail": "No import provider configured for this event."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    provider = config.provider
    if not provider.has_credentials:
        return Response(
            {"detail": "Provider has no credentials stored."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        raw_text = fetch_from_provider(provider)
    except ProviderLoginError as exc:
        return Response(
            {"detail": f"Provider login failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ProviderFetchError as exc:
        return Response(
            {"detail": f"Provider fetch failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    try:
        json_data = parse_json_with_duplicate_keys(raw_text)
    except (ValueError, TypeError) as exc:
        return Response(
            {"detail": f"Provider returned invalid JSON: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if not isinstance(json_data, dict):
        return Response(
            {"detail": "Provider JSON must be an object at the top level."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    prefixes = discover_child_prefixes(json_data)
    total_bookings = sum(1 for v in json_data.values() if isinstance(v, dict))
    return Response({"prefixes": prefixes, "total_bookings": total_bookings})
