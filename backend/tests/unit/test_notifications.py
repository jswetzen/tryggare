"""
Unit tests for notifications: provider selection and the SMTP/Null providers.
"""

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from notifications.apps import NotificationsConfig
from notifications.models import EmailSendLog
from notifications.providers import (
    DisabledProvider,
    NullProvider,
    SmtpProvider,
    get_provider,
)


class TestGetProvider:
    @override_settings(DEMO_MODE=False, EMAIL_HOST="smtp.simply.com")
    def test_returns_smtp_provider_when_configured(self):
        assert isinstance(get_provider(), SmtpProvider)

    @override_settings(DEMO_MODE=False, EMAIL_HOST="")
    def test_returns_disabled_provider_when_email_host_blank_and_not_demo(self):
        assert isinstance(get_provider(), DisabledProvider)

    @override_settings(DEMO_MODE=True, EMAIL_HOST="smtp.simply.com")
    def test_returns_null_provider_in_demo_mode_even_if_configured(self):
        assert isinstance(get_provider(), NullProvider)

    @override_settings(
        DEMO_MODE=False, EMAIL_HOST="smtp.simply.com", EMAIL_PROVIDER="mailgun"
    )
    def test_unknown_provider_raises_loudly(self):
        try:
            get_provider()
            raise AssertionError("expected ImproperlyConfigured")
        except ImproperlyConfigured:
            pass


class TestSmtpProvider:
    @pytest.mark.django_db
    def test_send_lands_in_outbox(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        SmtpProvider().send(
            to="guardian@example.com", subject="Subject", body="Body text"
        )
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["guardian@example.com"]
        assert sent.subject == "Subject"
        assert sent.body == "Body text"

    @pytest.mark.django_db
    def test_send_records_a_send_log_entry(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        SmtpProvider().send(to="guardian@example.com", subject="Subject", body="Body")
        assert EmailSendLog.objects.count() == 1

    @pytest.mark.django_db
    @override_settings(EMAIL_SEND_BUDGET_MAX=3)
    def test_refuses_to_send_past_budget(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        provider = SmtpProvider()
        for _ in range(3):
            provider.send(to="guardian@example.com", subject="s", body="b")
        assert len(mail.outbox) == 3

        provider.send(to="guardian@example.com", subject="s", body="b")

        assert len(mail.outbox) == 3
        assert EmailSendLog.objects.count() == 3

    @pytest.mark.django_db
    @override_settings(EMAIL_SEND_BUDGET_MAX=1, EMAIL_SEND_BUDGET_WINDOW_HOURS=4)
    def test_old_sends_outside_window_do_not_count_against_budget(self, settings):
        from datetime import timedelta

        from django.utils import timezone

        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        stale = EmailSendLog.objects.create()
        EmailSendLog.objects.filter(pk=stale.pk).update(
            sent_at=timezone.now() - timedelta(hours=5)
        )

        SmtpProvider().send(to="guardian@example.com", subject="s", body="b")

        assert len(mail.outbox) == 1


class TestNullProvider:
    def test_send_is_a_true_no_op(self, caplog):
        NullProvider().send(to="guardian@example.com", subject="Subject", body="Body")
        assert len(mail.outbox) == 0
        assert "guardian@example.com" in caplog.text

    def test_send_logs_the_body(self, caplog):
        NullProvider().send(
            to="guardian@example.com",
            subject="Verify your registration",
            body="Click https://example.com/verify/abc123 to confirm.",
        )
        assert "https://example.com/verify/abc123" in caplog.text


class TestDisabledProvider:
    def test_send_is_a_true_no_op(self, caplog):
        DisabledProvider().send(
            to="guardian@example.com", subject="Subject", body="Body"
        )
        assert len(mail.outbox) == 0

    def test_send_does_not_log_the_body_or_token(self, caplog):
        DisabledProvider().send(
            to="guardian@example.com",
            subject="Verify your registration",
            body="Click https://example.com/verify/abc123 to confirm.",
        )
        assert "https://example.com/verify/abc123" not in caplog.text
        assert "abc123" not in caplog.text

    def test_send_still_names_recipient_and_subject(self, caplog):
        DisabledProvider().send(
            to="guardian@example.com",
            subject="Verify your registration",
            body="Click https://example.com/verify/abc123 to confirm.",
        )
        assert "guardian@example.com" in caplog.text
        assert "Verify your registration" in caplog.text


class TestNotificationsConfigReady:
    """Startup-time refusal for an unconfigured (non-demo) deployment."""

    @override_settings(DEMO_MODE=True, EMAIL_HOST="", EMAIL_DISABLED_ACK=False)
    def test_demo_mode_boots_without_ack(self):
        NotificationsConfig("notifications", __import__("notifications")).ready()

    @override_settings(DEMO_MODE=False, EMAIL_HOST="smtp.simply.com")
    def test_configured_email_boots_without_ack(self):
        NotificationsConfig("notifications", __import__("notifications")).ready()

    @override_settings(DEMO_MODE=False, EMAIL_HOST="", EMAIL_DISABLED_ACK=True)
    def test_ack_boots_and_warns(self, caplog):
        NotificationsConfig("notifications", __import__("notifications")).ready()
        assert "EMAIL_DISABLED_ACK" in caplog.text

    @override_settings(DEMO_MODE=False, EMAIL_HOST="", EMAIL_DISABLED_ACK=False)
    def test_neither_refuses_to_start(self):
        try:
            NotificationsConfig("notifications", __import__("notifications")).ready()
            raise AssertionError("expected ImproperlyConfigured")
        except ImproperlyConfigured as e:
            assert "EMAIL_HOST" in str(e)
            assert "EMAIL_DISABLED_ACK" in str(e)
