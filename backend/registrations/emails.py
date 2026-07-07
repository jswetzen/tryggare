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
