"""Composes the two transactional messages self-serve registration sends.

Plain text, consistent with notifications/emails.py's existing style — no new
templating layer for two short messages. Never put allergy/health text here
(see notifications/providers.py's module docstring for why).
"""

from django.conf import settings
from django.utils.translation import gettext as _

from notifications.emails import send_transactional_email

from .models import Registration


def send_verification_email(registration: Registration, token: str) -> None:
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
    send_transactional_email(to=registration.contact_email, subject=subject, body=body)


def send_confirmation_email(registration: Registration) -> None:
    subject = _("Registration confirmed: %(event)s") % {
        "event": registration.event.name
    }
    body = _(
        "Your registration for %(event)s is confirmed. Your reference code is %(code)s."
    ) % {"event": registration.event.name, "code": registration.reference_code}
    send_transactional_email(to=registration.contact_email, subject=subject, body=body)


def send_payment_instructions_email(registration: Registration) -> None:
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
    send_transactional_email(
        to=registration.contact_email, subject=subject, body="\n".join(lines)
    )
