from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FeatureRequestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feature_requests"
    verbose_name = _("Feature requests")
