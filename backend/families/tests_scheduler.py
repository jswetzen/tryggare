"""Tests for the in-app GDPR retention scheduler's start guard.

should_start_scheduler() decides whether the current process is the
long-running daphne server (start the scheduler) vs. a one-off `manage.py`
invocation such as `test`/`migrate`/`makemigrations`/`shell` (don't). See
families/apps.py for the full reasoning.
"""

from unittest import mock

from django.test import SimpleTestCase

from families.apps import should_start_scheduler


class ShouldStartSchedulerTests(SimpleTestCase):
    def test_false_for_manage_py_bare(self):
        with mock.patch("sys.argv", ["manage.py", "test"]):
            self.assertFalse(should_start_scheduler())

    def test_false_for_manage_py_with_relative_path(self):
        with mock.patch("sys.argv", ["./manage.py", "migrate"]):
            self.assertFalse(should_start_scheduler())

    def test_false_for_manage_py_with_absolute_path(self):
        with mock.patch("sys.argv", ["/app/backend/manage.py", "makemigrations"]):
            self.assertFalse(should_start_scheduler())

    def test_false_for_manage_py_shell(self):
        with mock.patch("sys.argv", ["manage.py", "shell"]):
            self.assertFalse(should_start_scheduler())

    def test_true_for_daphne_module_invocation(self):
        # `python -m daphne ...` sets argv[0] to daphne's entry-point path,
        # never "manage.py" — this is how both dev and prod actually serve.
        with mock.patch(
            "sys.argv",
            [
                "/app/.venv/lib/python3.12/site-packages/daphne/__main__.py",
                "-b",
                "0.0.0.0",
                "-p",
                "8000",
                "config.asgi:application",
            ],
        ):
            self.assertTrue(should_start_scheduler())

    def test_true_for_empty_argv0(self):
        # Defensive: some embedding contexts leave argv[0] empty; treat
        # anything that isn't literally "manage.py" as "start it".
        with mock.patch("sys.argv", ["", "-m", "daphne"]):
            self.assertTrue(should_start_scheduler())

    def test_false_for_empty_argv(self):
        with mock.patch("sys.argv", []):
            self.assertFalse(should_start_scheduler())
