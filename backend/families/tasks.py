import logging

from django.core.management import call_command

logger = logging.getLogger(__name__)


def run_scheduled_retention():
    """Daily GDPR retention sweep.

    Thin wrapper around the ``anonymize_expired_data`` management command,
    scheduled by ``FamiliesConfig.ready()``. Anonymizes families inactive past
    ``DATA_RETENTION_DAYS`` and prunes ``AuditLog`` rows past
    ``AUDIT_LOG_RETENTION_DAYS`` (``--include-audit-logs``) — without this,
    audit logs grow forever since nothing else prunes them. Exceptions are
    caught and logged so a single failed run doesn't kill the scheduler's
    background thread (mirrors demo.tasks.reset_demo_data).
    """
    logger.info("GDPR retention: starting scheduled anonymize_expired_data run")
    try:
        call_command("anonymize_expired_data", "--include-audit-logs")
        logger.info("GDPR retention: scheduled run complete")
    except Exception:
        logger.exception("GDPR retention: scheduled run failed")
