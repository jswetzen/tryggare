import logging

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
    verbose_name = _("Notifications")

    def ready(self):
        from django.conf import settings

        if settings.DEMO_MODE or settings.EMAIL_HOST:
            # Either a supported no-email mode (DEMO_MODE) or email is
            # actually configured — nothing to check.
            return

        if settings.EMAIL_DISABLED_ACK:
            logger.warning(
                "Email is not configured (EMAIL_HOST is unset) and "
                "DEMO_MODE is off. EMAIL_DISABLED_ACK=true acknowledges "
                "this is deliberate: booting normally, but no verification, "
                "payment, or consent-renewal email will be sent — messages "
                "will be dropped (see notifications/providers.py "
                "DisabledProvider)."
            )
            return

        raise ImproperlyConfigured(
            "Email is not configured for this deployment: EMAIL_HOST is "
            "unset and DEMO_MODE is not enabled. Without one of these, "
            "verification/payment/consent emails would be silently dropped "
            "in what looks like a real production deployment. Fix by "
            "setting ONE of the following: (1) EMAIL_HOST (plus the other "
            "EMAIL_* settings) to actually send email, or (2) "
            "EMAIL_DISABLED_ACK=true to confirm you are deliberately "
            "running this deployment without email."
        )
