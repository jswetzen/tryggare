"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from families.views import ChildViewSet, FamilyViewSet, ParentViewSet
from families.qr_views import qr_info
from events.views import EventViewSet, SessionViewSet, TicketViewSet
from checkins.views import AuditLogViewSet, CheckInRecordViewSet
from accounts.views import csrf_token, check_auth, login_view, logout_view

# Create API router
router = DefaultRouter()

# Family management
router.register(r"families", FamilyViewSet, basename="family")
router.register(r"parents", ParentViewSet, basename="parent")
router.register(r"children", ChildViewSet, basename="child")

# Event management
router.register(r"events", EventViewSet, basename="event")
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"tickets", TicketViewSet, basename="ticket")

# Check-in management
router.register(r"checkins", CheckInRecordViewSet, basename="checkin")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    # Session-based authentication endpoints
    path("api/csrf/", csrf_token, name="csrf-token"),
    path("api/auth/check/", check_auth, name="auth-check"),
    path("api/auth/login/", login_view, name="auth-login"),
    path("api/auth/logout/", logout_view, name="auth-logout"),
    path("qr/<str:token>/", qr_info, name="qr-info"),  # Public QR code endpoint
]
