import logging

from django.core.management import call_command

logger = logging.getLogger(__name__)


def reset_demo_data():
    logger.info("Demo reset: starting hourly data clear & reseed")
    try:
        call_command("seed_demo_data", reset=True)
        logger.info("Demo reset: complete")
    except Exception:
        logger.exception("Demo reset: failed")
