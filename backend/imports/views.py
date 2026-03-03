import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from events.models import Event

from .importer import run_import
from .models import EventImportConfig, ImportRun
from .parser import discover_child_prefixes
from .serializers import (
    EventImportConfigSerializer,
    ImportRunListSerializer,
    ImportRunSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def discover_prefixes_view(request):
    """
    POST /api/imports/discover-prefixes/
    Body: {"json_data": {...}}

    Scans all bookings in the uploaded JSON and returns discovered child
    ticket prefixes with sample children and booking counts.
    """
    json_data = request.data.get("json_data")
    if not isinstance(json_data, dict):
        return Response(
            {"detail": "json_data must be a JSON object."},
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
    Body: {
        "json_data": {...},
        "field_mappings": {"prefix": "full_event" | "<session_uuid>" | "ignore", ...},
        "source_file_name": "export.json"  (optional)
    }

    Creates or updates EventImportConfig, runs import synchronously,
    returns the ImportRun with full results.
    """
    event = get_object_or_404(Event, pk=event_id)

    json_data = request.data.get("json_data")
    if not isinstance(json_data, dict):
        return Response(
            {"detail": "json_data must be a JSON object."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    field_mappings = request.data.get("field_mappings")
    if not isinstance(field_mappings, dict):
        return Response(
            {"detail": "field_mappings must be a JSON object."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    source_file_name = str(request.data.get("source_file_name", "")).strip()

    # Create or update the config
    config, _ = EventImportConfig.objects.get_or_create(event=event)
    config.field_mappings = field_mappings
    config.save()

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
