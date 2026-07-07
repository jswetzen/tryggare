import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RegistrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registrations"

    def ready(self):
        from families.apps import should_start_scheduler

        if not should_start_scheduler():
            return

        from apscheduler.schedulers.background import BackgroundScheduler

        from .tasks import sweep_expired_registrations

        scheduler = BackgroundScheduler()
        # Hourly, not daily like the GDPR retention sweep: a 48h TTL needs
        # finer granularity than a once-a-day cutoff would give guardians —
        # hourly keeps the window tight without meaningfully increasing load
        # (this table stays small).
        scheduler.add_job(
            sweep_expired_registrations,
            "interval",
            hours=1,
            id="registration_expiry_sweep",
        )
        scheduler.start()
        logger.info("Registration expiry sweep scheduler started (hourly)")
