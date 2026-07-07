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
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpProvider:
    """Sends via Django's SMTP email backend, configured from EMAIL_* settings."""

    def send(self, to: str, subject: str, body: str) -> None:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[to],
        )


class NullProvider:
    """No-op provider for deployments with no email configured (e.g. the demo instance)."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.warning("Email sending disabled/unconfigured; skipping send to %s", to)


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
