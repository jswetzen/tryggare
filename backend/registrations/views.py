import logging
from datetime import timedelta

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from checkins.audit import log_audit
from events.models import Event, EventTicket
from families.models import Parent
from families.services import create_family_with_members

from .emails import (
    send_confirmation_email,
    send_payment_instructions_email,
    send_verification_email,
)
from .models import (
    Payment,
    Registration,
    default_expires_at,
    default_payment_expires_at,
)
from .serializers import RegistrationSubmitSerializer
from .swish import payment_instructions
from .tokens import generate_verification_token, hash_token

logger = logging.getLogger(__name__)

RESEND_COOLDOWN = timedelta(minutes=10)


class RegistrationSubmitThrottle(AnonRateThrottle):
    """Deliberately loose (see settings.REST_FRAMEWORK's 'registration_submit'
    rate): on-site bulk registration from one venue wifi hotspot is a normal,
    confirmed workload for this product (the FestivalPro/Planning Center
    bulk-import precedent), so a tight per-IP cap would block legitimate use
    more than it stops abuse. The (event, contact_email) dedup+resend-cooldown
    path below is the actual abuse control."""

    scope = "registration_submit"


class RegistrationPaymentStatusThrottle(AnonRateThrottle):
    scope = "registration_payment_status"


def _create_registration(
    *, event, contact_email, last_name, parents_data, children_data
):
    family = create_family_with_members(
        last_name=last_name,
        parents_data=parents_data,
        children_data=children_data,
        consent_attestor_email=contact_email,
    )
    token = generate_verification_token()
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email=contact_email,
        verification_token_hash=hash_token(token),
        verification_sent_at=timezone.now(),
    )
    attendees = list(family.parents.all()) + list(family.children.all())
    for attendee in attendees:
        EventTicket.objects.create(
            attendee=attendee, event=event, registration=registration
        )
    return registration, token


def _resend_verification(registration):
    """Returns (registration, token, was_throttled)."""
    if (
        registration.verification_sent_at is not None
        and timezone.now() - registration.verification_sent_at < RESEND_COOLDOWN
    ):
        return registration, None, True

    token = generate_verification_token()
    registration.verification_token_hash = hash_token(token)
    registration.verification_sent_at = timezone.now()
    registration.expires_at = default_expires_at()
    registration.save(
        update_fields=["verification_token_hash", "verification_sent_at", "expires_at"]
    )
    return registration, token, False


@api_view(["GET"])
@permission_classes([AllowAny])
def registration_event_info(request, event_id):
    """
    Public, minimal event lookup for the /register/[eventId] form — just
    enough to render "Register for {name}" without exposing the full
    (staff-authenticated) EventViewSet to anonymous requests.
    """
    event = get_object_or_404(Event, pk=event_id)
    return Response(
        {
            "id": str(event.id),
            "name": event.name,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
            "is_paid": event.is_paid,
            "price": str(event.price) if event.price is not None else None,
            "currency": "SEK",
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegistrationSubmitThrottle])
def submit_registration(request):
    """
    Public, unauthenticated self-serve registration submission.

    Materializes Family/Parent/Child/EventTicket rows immediately
    (status=pending_verification) rather than deferring to a JSON blob — see
    the Track 1 plan for why (keeps special-category child data inside every
    existing compliance mechanism). A second submission for a still-pending
    (event, contact_email) pair resends the verification email instead of
    creating a duplicate row.
    """
    serializer = RegistrationSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Honeypot: real guardians never fill this hidden field. Respond as if
    # successful — bots shouldn't learn their submission was rejected —
    # without persisting anything.
    if data.get("website"):
        logger.warning("Registration honeypot triggered for event %s", data["event"].id)
        return Response(
            {
                "reference_code": None,
                "message": _("Thanks — check your email to confirm."),
            },
            status=status.HTTP_201_CREATED,
        )

    event = data["event"]
    contact_email = data["contact_email"]

    existing = (
        Registration.objects.filter(
            event=event,
            contact_email=contact_email,
            status=Registration.Status.PENDING_VERIFICATION,
        )
        .order_by("-submitted_at")
        .first()
    )

    if existing is not None and not existing.is_expired:
        registration, token, throttled = _resend_verification(existing)
        if throttled:
            return Response(
                {
                    "reference_code": registration.reference_code,
                    "message": _(
                        "A confirmation email was already sent recently — "
                        "please check your inbox."
                    ),
                },
                status=status.HTTP_200_OK,
            )
        send_verification_email(registration, token)
        log_audit(
            request,
            action="registration_resent",
            entity_type="Registration",
            entity_id=str(registration.id),
            details={"reference_code": registration.reference_code},
        )
        return Response(
            {
                "reference_code": registration.reference_code,
                "message": _("Thanks — check your email to confirm."),
            },
            status=status.HTTP_201_CREATED,
        )

    with transaction.atomic():
        registration, token = _create_registration(
            event=event,
            contact_email=contact_email,
            last_name=data.get("last_name", ""),
            parents_data=data.get("parents", []),
            children_data=data.get("children", []),
        )

    send_verification_email(registration, token)

    log_audit(
        request,
        action="registration_submitted",
        entity_type="Registration",
        entity_id=str(registration.id),
        details={
            "event_id": str(event.id),
            "reference_code": registration.reference_code,
        },
    )

    return Response(
        {
            "reference_code": registration.reference_code,
            "message": _("Thanks — check your email to confirm."),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_registration(request, token):
    """
    Public verification-link landing endpoint.

    Auto-confirms the common case. Exception, checked first and
    unconditionally: if the now-verified contact_email exactly matches an
    existing, non-anonymized Parent.email on a *different* family, route to
    pending_review instead of auto-attaching — since email verification is
    the entire security control here, defeating auto-attach doesn't require
    spoofing anything, only the real mailbox owner clicking a routine link
    out of habit (divorced co-parents; anyone who knows a family's contact
    email from a church directory). Only when that doesn't match do we look
    at whether the event is paid: a paid event routes to pending_payment
    instead of confirmed, and gets a Payment record + payment instructions
    email instead of a confirmation email.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("event", "family"),
        verification_token_hash=hash_token(token),
        status=Registration.Status.PENDING_VERIFICATION,
    )

    if registration.is_expired:
        return Response(
            {"error": _("This verification link has expired.")},
            status=status.HTTP_410_GONE,
        )

    email_matches_other_family = (
        Parent.objects.filter(
            email=registration.contact_email, anonymized_at__isnull=True
        )
        .exclude(family=registration.family)
        .exists()
    )

    event = registration.event
    payment = None

    if email_matches_other_family:
        registration.status = Registration.Status.PENDING_REVIEW
    elif event.is_paid:
        registration.status = Registration.Status.PENDING_PAYMENT
        registration.expires_at = default_payment_expires_at()
    else:
        registration.status = Registration.Status.CONFIRMED

    registration.verified_at = timezone.now()
    update_fields = ["verified_at", "status"]
    if registration.status == Registration.Status.PENDING_PAYMENT:
        update_fields.append("expires_at")
    registration.save(update_fields=update_fields)

    if event.is_paid:
        payment = Payment.objects.create(registration=registration, amount=event.price)

    log_audit(
        request,
        action="registration_verified",
        entity_type="Registration",
        entity_id=str(registration.id),
        details={
            "reference_code": registration.reference_code,
            "status": registration.status,
        },
    )

    if registration.status == Registration.Status.CONFIRMED:
        send_confirmation_email(registration)
    elif registration.status == Registration.Status.PENDING_PAYMENT:
        send_payment_instructions_email(registration)

    response_data = {
        "status": registration.status,
        "reference_code": registration.reference_code,
        "event_name": registration.event.name,
    }
    if payment is not None:
        response_data.update(payment_instructions(payment))

    return Response(response_data)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegistrationPaymentStatusThrottle])
def registration_payment_status(request):
    """
    Public "check my payment status" lookup — the recovery path for a
    guardian who navigated away from verify_registration's one-time response
    before paying. Keyed on (reference_code, contact_email) rather than
    reference_code alone: unlike the high-entropy verification token, the
    8-character reference_code is shown to guardians for support lookups and
    isn't meant to be a secret credential on its own. POST, not GET with
    query params, so contact_email doesn't land in access logs the way a
    query string would.
    """
    reference_code = request.data.get("reference_code", "").strip().upper()
    contact_email = request.data.get("contact_email", "").strip()

    registration = get_object_or_404(
        Registration.objects.select_related("event", "payment"),
        reference_code=reference_code,
        contact_email__iexact=contact_email,
    )

    if not registration.event.is_paid or not hasattr(registration, "payment"):
        raise Http404("No payment associated with this registration")

    log_audit(
        request,
        action="registration_payment_status_checked",
        entity_type="Registration",
        entity_id=str(registration.id),
        details={"reference_code": registration.reference_code},
    )

    return Response(
        {
            "status": registration.status,
            "event_name": registration.event.name,
            **payment_instructions(registration.payment),
        }
    )
