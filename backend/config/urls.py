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
    path("api/auth/", include("rest_framework.urls")),  # Login/logout endpoints
    path("qr/<str:token>/", qr_info, name="qr-info"),  # Public QR code endpoint
]
