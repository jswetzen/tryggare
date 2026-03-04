"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from families.views import ChildViewSet, FamilyViewSet, ParentViewSet
from families.qr_views import qr_info
from events.views import EventViewSet, EventTicketViewSet, SessionViewSet, SessionTicketViewSet, TicketViewSet
from checkins.views import AuditLogViewSet, CheckInRecordViewSet, PrintQueueViewSet
from accounts.views import csrf_token, check_auth, login_view, logout_view
from imports.views import (
    discover_prefixes_view,
    discover_prefixes_from_provider_view,
    get_import_config,
    import_history,
    list_create_provider_view,
    provider_detail_view,
    run_import_view,
    set_config_provider_view,
)

# Create API router
router = DefaultRouter()

# Family management
router.register(r"families", FamilyViewSet, basename="family")
router.register(r"parents", ParentViewSet, basename="parent")
router.register(r"children", ChildViewSet, basename="child")

# Event management
router.register(r"events", EventViewSet, basename="event")
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"tickets", TicketViewSet, basename="ticket")  # DEPRECATED
router.register(r"event-tickets", EventTicketViewSet, basename="event-ticket")
router.register(r"session-tickets", SessionTicketViewSet, basename="session-ticket")

# Check-in management
router.register(r"checkins", CheckInRecordViewSet, basename="checkin")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"print-queue", PrintQueueViewSet, basename="print-queue")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    # Session-based authentication endpoints
    path("api/csrf/", csrf_token, name="csrf-token"),
    path("api/auth/check/", check_auth, name="auth-check"),
    path("api/auth/login/", login_view, name="auth-login"),
    path("api/auth/logout/", logout_view, name="auth-logout"),
    path("api/qr/<str:code>/", qr_info, name="qr-info"),  # Public QR code endpoint (privacy-first)
    # Import endpoints (must be before the catch-all)
    path("api/imports/discover-prefixes/", discover_prefixes_view, name="import-discover-prefixes"),
    path("api/imports/providers/", list_create_provider_view, name="import-providers"),
    path("api/imports/providers/<uuid:provider_id>/", provider_detail_view, name="import-provider-detail"),
    path("api/imports/events/<uuid:event_id>/config/", get_import_config, name="import-config"),
    path("api/imports/events/<uuid:event_id>/config/provider/", set_config_provider_view, name="import-config-provider"),
    path("api/imports/events/<uuid:event_id>/run/", run_import_view, name="import-run"),
    path("api/imports/events/<uuid:event_id>/history/", import_history, name="import-history"),
    path("api/imports/events/<uuid:event_id>/discover-prefixes/", discover_prefixes_from_provider_view, name="import-discover-prefixes-from-provider"),
    # Serve frontend SPA - catch-all for client-side routing (must be last)
    # Exclude admin/, api/, and SvelteKit's __data.json endpoints from catch-all
    # WhiteNoise middleware serves static files (_app/*) before this is reached
    re_path(r"^(?!admin/)(?!api/)(?!.*__data\.json).*$", TemplateView.as_view(template_name="index.html"), name="frontend"),
]
