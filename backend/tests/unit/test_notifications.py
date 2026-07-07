"""
Unit tests for notifications: provider selection and the SMTP/Null providers.
"""

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from notifications.providers import NullProvider, SmtpProvider, get_provider


class TestGetProvider:
    @override_settings(DEMO_MODE=False, EMAIL_HOST="smtp.simply.com")
    def test_returns_smtp_provider_when_configured(self):
        assert isinstance(get_provider(), SmtpProvider)

    @override_settings(DEMO_MODE=False, EMAIL_HOST="")
    def test_returns_null_provider_when_email_host_blank(self):
        assert isinstance(get_provider(), NullProvider)

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


class TestNullProvider:
    def test_send_is_a_true_no_op(self, caplog):
        NullProvider().send(to="guardian@example.com", subject="Subject", body="Body")
        assert len(mail.outbox) == 0
        assert "guardian@example.com" in caplog.text
