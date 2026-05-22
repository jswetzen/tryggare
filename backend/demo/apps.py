import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DemoConfig(AppConfig):
    name = "demo"

    def ready(self):
        if os.getenv("DEMO_MODE", "false").lower() != "true":
            return
        # Django's dev reloader forks: the parent process (RUN_MAIN unset) loads
        # apps but shouldn't start threads. The child (RUN_MAIN=true) is the real
        # server. In production (Daphne) RUN_MAIN is never set, so we start there.
        run_main = os.getenv("RUN_MAIN")
        if run_main is not None and run_main != "true":
            return

        from apscheduler.schedulers.background import BackgroundScheduler

        from .tasks import reset_demo_data

        scheduler = BackgroundScheduler()
        scheduler.add_job(reset_demo_data, "interval", hours=1, id="demo_reset")
        scheduler.start()
        logger.info("Demo mode: hourly reset scheduler started")
