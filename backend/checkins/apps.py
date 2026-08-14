from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CheckinsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "checkins"
    verbose_name = _("Check-In")
