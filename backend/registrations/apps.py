import logging

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class RegistrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registrations"
    verbose_name = _("Registrations")

    def ready(self):
        from families.apps import should_start_scheduler

        if not should_start_scheduler():
            return

        from apscheduler.schedulers.background import BackgroundScheduler

        from .tasks import run_registration_sweeps

        scheduler = BackgroundScheduler()
        # Hourly, not daily like the GDPR retention sweep: a 48h TTL needs
        # finer granularity than a once-a-day cutoff would give guardians —
        # hourly keeps the window tight without meaningfully increasing load
        # (this table stays small). run_registration_sweeps() runs both the
        # unverified-registration hard-delete pass and the unpaid-registration
        # cancel pass.
        scheduler.add_job(
            run_registration_sweeps,
            "interval",
            hours=1,
            id="registration_expiry_sweep",
        )
        scheduler.start()
        logger.info("Registration expiry sweep scheduler started (hourly)")
