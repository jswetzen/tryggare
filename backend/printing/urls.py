from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrinterViewSet, PrintJobViewSet

router = DefaultRouter()
router.register(r"printers", PrinterViewSet, basename="printer")
router.register(r"jobs", PrintJobViewSet, basename="print-job")

urlpatterns = [
    path("", include(router.urls)),
]
