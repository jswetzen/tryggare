import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .importer import ProviderFetchError, ProviderLoginError, run_import
from .models import FestivalProImportSource, ImportRun, ImportSource
from .parser import discover_child_prefixes, parse_json_with_duplicate_keys
from .serializers import (
    ImportSourceSerializer,
    ImportRunListSerializer,
    ImportRunSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAdminUser])
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


# ── Source CRUD ────────────────────────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def list_create_source_view(request):
    """GET /api/imports/sources/ or POST /api/imports/sources/"""
    if request.method == "GET":
        sources = ImportSource.objects.select_related("festivalpro_config", "event").all()
        return Response(ImportSourceSerializer(sources, many=True).data)
    serializer = ImportSourceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    source = serializer.save()
    return Response(
        ImportSourceSerializer(source).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAdminUser])
def source_detail_view(request, source_id):
    """GET/PUT/DELETE /api/imports/sources/<source_id>/"""
    source = get_object_or_404(
        ImportSource.objects.select_related("festivalpro_config", "event"),
        pk=source_id,
    )
    if request.method == "GET":
        return Response(ImportSourceSerializer(source).data)
    if request.method == "PUT":
        serializer = ImportSourceSerializer(source, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            ImportSourceSerializer(
                ImportSource.objects.select_related("festivalpro_config", "event").get(pk=updated.pk)
            ).data
        )
    source.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def run_import_source_view(request, source_id):
    """
    POST /api/imports/sources/<source_id>/run/

    Two modes:
    1. Manual file upload:
       Body: {"json_string": "...", "field_mappings": {...}, "source_file_name": "..."}
    2. Auto-fetch from source (json_string omitted):
       Body: {"field_mappings": {...}}
       Requires FestivalProImportSource with credentials.
    """
    source = get_object_or_404(
        ImportSource.objects.select_related("festivalpro_config"),
        pk=source_id,
    )

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
        if source.provider_type != ImportSource.PROVIDER_FESTIVALPRO:
            return Response(
                {"detail": "Auto-fetch is only supported for FestivalPro sources."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fp_config = getattr(source, "festivalpro_config", None)
        if fp_config is None:
            return Response(
                {"detail": "No FestivalPro config found for this source."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not source.has_credentials:
            return Response(
                {"detail": "Source has no credentials stored."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .providers import get_provider
        provider = get_provider(source)
        try:
            raw_text = provider.fetch(source)
        except ProviderLoginError as exc:
            logger.warning("Provider login error for source %s: %s", source_id, exc)
            return Response(
                {"detail": f"Provider login failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ProviderFetchError as exc:
            logger.warning("Provider fetch error for source %s: %s", source_id, exc)
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
        source_file_name = f"auto-fetch:{source.name}"

    # Save field_mappings to FestivalPro config if applicable
    if source.provider_type == ImportSource.PROVIDER_FESTIVALPRO:
        fp_config, _ = FestivalProImportSource.objects.get_or_create(source=source)
        fp_config.field_mappings = field_mappings
        fp_config.save(update_fields=["field_mappings"])

    # Run the import synchronously
    try:
        import_run = run_import(json_data, source, field_mappings, request.user)
        import_run.source_file_name = source_file_name
        import_run.raw_data = json_data
        import_run.save(update_fields=["source_file_name", "raw_data"])
    except Exception as exc:
        logger.exception("Unhandled error during import for source %s", source_id)
        return Response(
            {"detail": f"Import failed: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(ImportRunSerializer(import_run).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def import_history_source_view(request, source_id):
    """
    GET /api/imports/sources/<source_id>/history/

    Returns ImportRun list for this source, newest first.
    """
    source = get_object_or_404(ImportSource, pk=source_id)
    runs = ImportRun.objects.filter(source=source).order_by("-started_at")
    return Response(ImportRunListSerializer(runs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def discover_prefixes_from_source_view(request, source_id):
    """
    POST /api/imports/sources/<source_id>/discover-prefixes/

    Fetches data from the source's provider and runs discover_child_prefixes.
    Returns {prefixes, total_bookings} — same shape as the top-level discover-prefixes endpoint.
    """
    source = get_object_or_404(
        ImportSource.objects.select_related("festivalpro_config"),
        pk=source_id,
    )
    if source.provider_type != ImportSource.PROVIDER_FESTIVALPRO:
        return Response(
            {"detail": "Auto-fetch is only supported for FestivalPro sources."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    fp_config = getattr(source, "festivalpro_config", None)
    if fp_config is None:
        return Response(
            {"detail": "No FestivalPro config found for this source."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not source.has_credentials:
        return Response(
            {"detail": "Source has no credentials stored."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    from .providers import get_provider
    provider = get_provider(source)
    try:
        raw_text = provider.fetch(source)
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
