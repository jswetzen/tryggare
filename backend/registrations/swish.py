"""Swish deep-link/QR construction for paid-event payment instructions.

Pure URL templating — no external API call, no merchant credentials, no
certificate. A Swish payment request is just a deep-link URL the payer's own
Swish app opens (see docs/roadmap/payment_processing.md). This is why Phase 2
needs no pluggable provider interface the way notifications/providers.py does
for email: there is nothing here to swap out an implementation behind — both
Swish and Bankgiro are 100% staff-verified manually in this phase.
"""

import base64
import io
from decimal import Decimal
from urllib.parse import quote

import qrcode
from django.conf import settings

from .models import Payment

SWISH_URL_TEMPLATE = "https://app.swish.nu/1/p/sw/?sw={payee}&amt={amount}&cur=SEK&msg={reference}&src=qr"


def build_swish_url(*, payee_number: str, amount: Decimal, reference: str) -> str:
    return SWISH_URL_TEMPLATE.format(
        payee=quote(payee_number),
        amount=amount,
        reference=quote(reference),
    )


def build_qr_data_url(url: str) -> str:
    """Same qrcode-library pattern as checkins/views.py::print_page, with a
    larger box_size tuned for on-screen display rather than a 54mm label."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def payment_instructions(payment: Payment) -> dict:
    """Assembled payload returned both inline by verify_registration (the
    pending_payment case) and by the payment-status lookup endpoint.

    Uses payment.balance, not payment.amount — a guardian who already paid
    part of the total and returns via the payment-status recovery page must
    be asked for what's actually still owed, not the original nominal
    amount (which would silently invite an overpayment).

    swish_url/swish_qr_data_url are None when SWISH_PAYEE_NUMBER isn't
    configured — blank-safe, matching the DATA_CONTROLLER_* convention, since
    not every deployment/congregation will have set one up.
    """
    balance = payment.balance
    swish_url = None
    swish_qr_data_url = None
    if settings.SWISH_PAYEE_NUMBER:
        swish_url = build_swish_url(
            payee_number=settings.SWISH_PAYEE_NUMBER,
            amount=balance,
            reference=payment.reference_code,
        )
        swish_qr_data_url = build_qr_data_url(swish_url)

    return {
        "amount": str(balance),
        "currency": payment.currency,
        "reference_code": payment.reference_code,
        "swish_url": swish_url,
        "swish_qr_data_url": swish_qr_data_url,
        "bankgiro_number": settings.BANKGIRO_NUMBER or None,
    }
