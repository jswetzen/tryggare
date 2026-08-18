"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from families.views import ChildViewSet, FamilyViewSet, ParentViewSet
from families.qr_views import privacy_info, qr_info, qr_reveal_safety_info
from events.views import (
    EventViewSet,
    EventTicketViewSet,
    SessionViewSet,
    SessionTicketViewSet,
    TicketViewSet,
)
from checkins.views import AuditLogViewSet, CheckInRecordViewSet, PrintQueueViewSet
from reports.views import EventReportViewSet
from accounts.views import csrf_token, check_auth, login_view, logout_view
from imports.views import (
    discover_prefixes_view,
    discover_prefixes_from_source_view,
    import_history_source_view,
    list_create_source_view,
    run_import_planningcenter_view,
    run_import_source_view,
    source_detail_view,
)
from printing.views import label_page_view
from registrations.views import (
    confirm_registration_despite_balance_view,
    mark_registration_paid,
    registration_event_info,
    registration_payment_status,
    submit_registration,
    validate_promo_code,
    verify_registration,
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

# Reporting
router.register(r"event-reports", EventReportViewSet, basename="event-report")

urlpatterns = [
    # Django's built-in language-switch endpoint (POST language=<code>, sets
    # the session + LANGUAGE_COOKIE_NAME cookie, then redirects to `next`).
    # Mounted under admin/ so it's covered by the SPA catch-all's existing
    # `(?!admin/)` exclusion below without touching that regex.
    path("admin/i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    # Session-based authentication endpoints
    path("api/csrf/", csrf_token, name="csrf-token"),
    path("api/auth/check/", check_auth, name="auth-check"),
    path("api/auth/login/", login_view, name="auth-login"),
    path("api/auth/logout/", logout_view, name="auth-logout"),
    path(
        "api/qr/<str:code>/", qr_info, name="qr-info"
    ),  # Public QR code endpoint (privacy-first)
    path(
        "api/qr/<str:code>/reveal-safety-info/",
        qr_reveal_safety_info,
        name="qr-reveal-safety-info",
    ),  # Public, throttled reveal for allergy/medical-notes text (logged separately from qr_viewed)
    path(
        "api/privacy/", privacy_info, name="privacy-info"
    ),  # Public data-controller info for the privacy page/notice
    # Public self-serve registration endpoints (unauthenticated, own throttle scope)
    path("api/registrations/", submit_registration, name="registration-submit"),
    path(
        "api/registrations/verify/<str:token>/",
        verify_registration,
        name="registration-verify",
    ),
    path(
        "api/registrations/events/<uuid:event_id>/",
        registration_event_info,
        name="registration-event-info",
    ),
    path(
        "api/registrations/payment-status/",
        registration_payment_status,
        name="registration-payment-status",
    ),
    path(
        "api/registrations/validate-promo-code/",
        validate_promo_code,
        name="registration-validate-promo-code",
    ),
    # Staff-authenticated check-in screen actions (case catalog §9.3)
    path(
        "api/registrations/<uuid:registration_id>/mark-paid/",
        mark_registration_paid,
        name="registration-mark-paid",
    ),
    path(
        "api/registrations/<uuid:registration_id>/confirm-despite-balance/",
        confirm_registration_despite_balance_view,
        name="registration-confirm-despite-balance",
    ),
    # Import endpoints (must be before the catch-all)
    path(
        "api/imports/discover-prefixes/",
        discover_prefixes_view,
        name="import-discover-prefixes",
    ),
    path("api/imports/sources/", list_create_source_view, name="import-sources"),
    path(
        "api/imports/sources/<uuid:source_id>/",
        source_detail_view,
        name="import-source-detail",
    ),
    path(
        "api/imports/sources/<uuid:source_id>/run/",
        run_import_source_view,
        name="import-source-run",
    ),
    path(
        "api/imports/sources/<uuid:source_id>/history/",
        import_history_source_view,
        name="import-source-history",
    ),
    path(
        "api/imports/sources/<uuid:source_id>/run-planningcenter/",
        run_import_planningcenter_view,
        name="import-source-run-planningcenter",
    ),
    path(
        "api/imports/sources/<uuid:source_id>/discover-prefixes/",
        discover_prefixes_from_source_view,
        name="import-source-discover-prefixes",
    ),
    # Printing app
    path("api/printing/", include("printing.urls")),
    path("print-job/<uuid:job_uuid>/label/", label_page_view, name="print-job-label"),
    # Serve frontend SPA - catch-all for client-side routing (must be last)
    # Exclude admin/, api/, and SvelteKit's __data.json endpoints from catch-all
    # WhiteNoise middleware serves static files (_app/*) before this is reached
    re_path(
        r"^(?!admin/)(?!api/)(?!.*__data\.json).*$",
        TemplateView.as_view(template_name="index.html"),
        name="frontend",
    ),
]
