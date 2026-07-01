import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def should_start_scheduler() -> bool:
    """Decide whether this process should start the in-app job scheduler.

    Unlike ``demo``'s scheduler (opt-in via ``DEMO_MODE``), the GDPR retention
    sweep needs to run by default in every real deployment — that's the whole
    point, so self-hosters don't have to wire external cron themselves. So we
    can't gate on an opt-in env var; we need to distinguish "this process is
    the long-running server" from "this process is a one-off management
    command" (``test``, ``migrate``, ``makemigrations``, ``shell``, seed
    commands, etc.) — ``AppConfig.ready()`` runs for both.

    Every one-off invocation goes through ``manage.py`` (``sys.argv[0]`` is
    ``manage.py``). The real server, in both dev (``docker-compose.yml``) and
    prod (``Dockerfile.prod`` / ``docker-compose.prod.yml`` /
    ``docker-compose.portainer.yml``), is launched directly as
    ``python -m daphne ...`` — never via ``manage.py runserver`` — so its
    ``sys.argv[0]`` is daphne's entry point, not ``manage.py``. Gating on that
    reliably tells "serving" apart from "tooling" without an extra env var.
    """
    if not sys.argv:
        return False
    return os.path.basename(sys.argv[0]) != "manage.py"


class FamiliesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "families"

    def ready(self):
        if not should_start_scheduler():
            return

        # No RUN_MAIN fork-guard here (unlike demo/apps.py): that guard exists
        # to stop Django's `runserver` autoreloader from double-starting the
        # scheduler in its unwatched parent process. This repo never runs
        # `manage.py runserver` — dev and prod both serve via daphne, which
        # doesn't fork/autoreload — and the should_start_scheduler() check
        # above already excludes every manage.py invocation outright
        # (including a hypothetical `runserver`), so RUN_MAIN would be dead
        # code here.
        from apscheduler.schedulers.background import BackgroundScheduler

        from .tasks import run_scheduled_retention

        scheduler = BackgroundScheduler()
        # Daily at 03:00 server time: retention/anonymization only cares about
        # day-granularity cutoffs (DATA_RETENTION_DAYS / AUDIT_LOG_RETENTION_DAYS),
        # so there's nothing to gain from running more often than once a day,
        # and running at 3am keeps the sweep off peak check-in hours (matching
        # the 3am-cron time previously documented in
        # anonymize_expired_data's docstring).
        scheduler.add_job(
            run_scheduled_retention,
            "cron",
            hour=3,
            minute=0,
            id="gdpr_retention",
        )
        scheduler.start()
        logger.info("GDPR retention scheduler started (daily at 03:00)")
