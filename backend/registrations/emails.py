"""Composes the two transactional messages self-serve registration sends.

Plain text, consistent with notifications/emails.py's existing style — no new
templating layer for two short messages. Never put allergy/health text here
(see notifications/providers.py's module docstring for why).
"""

import logging

from django.conf import settings
from django.utils.translation import gettext as _

from notifications.emails import send_transactional_email

from .models import Registration

logger = logging.getLogger(__name__)


def _send_or_degrade(
    *, to: str, subject: str, body: str, registration: Registration
) -> bool:
    """Sends, and reports delivery as a value instead of an exception.

    Every caller below runs in a request path *after* the registration or
    payment row has already committed, so letting an SMTP error propagate
    would 500 an operation that actually succeeded — telling the guardian (or
    a staff member confirming a payment) that nothing happened when in fact
    everything did, and inviting them to redo it. The write is the product of
    the request; the email is best-effort on top of it.

    Follows SmtpProvider.send()'s send-budget circuit breaker, which already
    logs-and-returns rather than raising — same "degrade, don't raise" model,
    not a second one. Callers surface the False case honestly and point at the
    existing resend path.

    Deliberately broad: a relay failure reaches us as smtplib.SMTPException,
    but a DNS failure, TLS error, or connection timeout arrives as OSError or
    ssl.SSLError, and none of those should behave differently here. The
    management command ``send_test_email`` bypasses this entirely (it calls
    the provider directly) so an operator testing SMTP still gets a traceback.
    """
    try:
        send_transactional_email(to=to, subject=subject, body=body)
        return True
    except Exception:
        logger.exception(
            "Failed to send %r for registration %s (%s) to %s — the registration "
            "itself is unaffected; the guardian can use the resend action.",
            subject,
            registration.reference_code,
            registration.id,
            to,
        )
        return False


def send_verification_email(registration: Registration, token: str) -> bool:
    verify_url = f"{settings.FRONTEND_BASE_URL}/register/verify/{token}"
    subject = _("Confirm your registration for %(event)s") % {
        "event": registration.event.name
    }
    body = _(
        "Thanks for registering for %(event)s!\n\n"
        "Please confirm your email address by visiting the link below:\n"
        "%(url)s\n\n"
        "This link expires in 48 hours. Your reference code is %(code)s."
    ) % {
        "event": registration.event.name,
        "url": verify_url,
        "code": registration.reference_code,
    }
    return _send_or_degrade(
        to=registration.contact_email,
        subject=subject,
        body=body,
        registration=registration,
    )


def send_confirmation_email(registration: Registration) -> bool:
    subject = _("Registration confirmed: %(event)s") % {
        "event": registration.event.name
    }
    body = _(
        "Your registration for %(event)s is confirmed. Your reference code is %(code)s."
    ) % {"event": registration.event.name, "code": registration.reference_code}
    return _send_or_degrade(
        to=registration.contact_email,
        subject=subject,
        body=body,
        registration=registration,
    )


def send_payment_instructions_email(registration: Registration) -> bool:
    """Sent instead of send_confirmation_email() when a paid-event
    registration reaches pending_payment. Plain text only, consistent with
    notifications/providers.py's protocol — the Swish link is included as a
    plain clickable URL (opened on the guardian's own phone, which has the
    Swish app installed) rather than an embedded QR image, since that would
    require extending the NotificationProvider protocol with attachment
    support for a case a plain link already covers."""
    from .swish import payment_instructions

    payment = registration.payment
    instructions = payment_instructions(payment)
    status_url = (
        f"{settings.FRONTEND_BASE_URL}/register/payment-status"
        f"?ref={registration.reference_code}"
    )

    subject = _("Payment needed to confirm your registration: %(event)s") % {
        "event": registration.event.name
    }
    lines = [
        _(
            "Your registration for %(event)s is verified, but not yet "
            "confirmed — payment of %(amount)s %(currency)s is needed first."
        )
        % {
            "event": registration.event.name,
            "amount": instructions["amount"],
            "currency": instructions["currency"],
        },
        "",
        _("Your reference code is %(code)s.") % {"code": registration.reference_code},
    ]
    if instructions["swish_url"]:
        lines += [
            "",
            _("Pay with Swish: %(url)s") % {"url": instructions["swish_url"]},
        ]
    if instructions["bankgiro_number"]:
        lines += [
            "",
            _("Or pay via Bankgiro to %(bankgiro)s, using %(code)s as the message.")
            % {
                "bankgiro": instructions["bankgiro_number"],
                "code": registration.reference_code,
            },
        ]
    lines += [
        "",
        _("Check your payment status any time at: %(url)s") % {"url": status_url},
    ]
    return _send_or_degrade(
        to=registration.contact_email,
        subject=subject,
        body="\n".join(lines),
        registration=registration,
    )
