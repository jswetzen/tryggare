"""
Pluggable transactional-email sending.

Two hard constraints, both surfaced while wiring this up for Simply.com's
SMTP relay (the first real provider):

- Never put allergy/health text (or any Art. 9 data) in an email body —
  once sent, it lives in the guardian's inbox and the provider's own logs
  indefinitely, outside this app's retention/anonymization pipeline.
- This path is for transactional mail only (confirmations, receipts,
  consent-renewal notices). Simply's terms of service prohibit
  newsletters/bulk mail through smtp.simply.com and cap volume around
  300 messages/4h — a bulk/marketing sender needs an entirely different
  provider, not just a different call site.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpProvider:
    """Sends via Django's SMTP email backend, configured from EMAIL_* settings."""

    def send(self, to: str, subject: str, body: str) -> None:
        from .models import EmailSendLog

        window_start = timezone.now() - timedelta(
            hours=settings.EMAIL_SEND_BUDGET_WINDOW_HOURS
        )
        recent_sends = EmailSendLog.objects.filter(sent_at__gte=window_start).count()
        if recent_sends >= settings.EMAIL_SEND_BUDGET_MAX:
            # Refuse rather than raise: a burst (e.g. a registration spam wave)
            # must not take down the shared channel for everything else that
            # sends through it, and the caller (a request handler) shouldn't
            # 500 just because the mailbox side of a feature is degraded.
            logger.error(
                "Send-budget circuit breaker tripped (%d sends in the last %dh); "
                "refusing to send to %s",
                recent_sends,
                settings.EMAIL_SEND_BUDGET_WINDOW_HOURS,
                to,
            )
            return

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[to],
        )
        EmailSendLog.objects.create()


class NullProvider:
    """No-op provider for deployments with no email configured (e.g. the demo instance)."""

    def send(self, to: str, subject: str, body: str) -> None:
        # Logging the body (not just the recipient) is deliberate here: in
        # DEMO_MODE — the exact environment self-serve registration gets
        # tested in — this log line is the only way to recover a
        # verification link, since no real inbox exists to check.
        logger.warning(
            "Email sending disabled/unconfigured; skipping send to %s\nSubject: %s\n%s",
            to,
            subject,
            body,
        )


_PROVIDERS: dict[str, type[NotificationProvider]] = {
    "smtp": SmtpProvider,
}


def get_provider() -> NotificationProvider:
    """
    Returns NullProvider whenever email isn't configured or is deliberately
    disabled (DEMO_MODE) — both are supported deployment states, not error
    conditions. Otherwise dispatches on EMAIL_PROVIDER; an unrecognised
    value fails loudly here rather than silently falling back to a no-op.
    """
    if settings.DEMO_MODE or not settings.EMAIL_HOST:
        return NullProvider()

    try:
        provider_cls = _PROVIDERS[settings.EMAIL_PROVIDER]
    except KeyError:
        raise ImproperlyConfigured(
            f"Unknown EMAIL_PROVIDER {settings.EMAIL_PROVIDER!r}; "
            f"expected one of {sorted(_PROVIDERS)}."
        ) from None
    return provider_cls()
