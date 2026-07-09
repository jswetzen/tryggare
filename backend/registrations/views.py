import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from checkins.audit import log_audit
from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    PromoCode,
    RegistrationWindowStatus,
    SessionTicket,
    TicketType,
)
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
    RegistrationExtra,
    default_payment_expires_at,
)
from .pricing import calculate_discount, calculate_total
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


class ValidatePromoCodeThrottle(AnonRateThrottle):
    scope = "registration_validate_promo_code"


def _split_selections(items):
    """Given a list of submitted parent/child dicts (each possibly carrying
    the registration-only ``ticket_type``/``extras`` keys added by
    RegistrationParentSerializer/RegistrationChildSerializer), return
    ``(model_data, selections)`` — ``model_data`` has those two keys
    stripped, so it's safe to pass straight to
    ``create_family_with_members`` (which only knows Parent/Child model
    fields), while ``selections`` carries them separately in the same
    order for the ticket/extras materialization pass below.
    """
    model_data = []
    selections = []
    for item in items:
        item = dict(item)
        selections.append(
            {
                "ticket_type": item.pop("ticket_type", None),
                "extras": item.pop("extras", []),
            }
        )
        model_data.append(item)
    return model_data, selections


def _ticket_type_payload(ticket_type):
    """Shared public JSON shape for a TicketType — used both by
    registration_event_info's normal listing and validate_promo_code's
    unlocked-types payload, so the two never drift apart."""
    return {
        "id": str(ticket_type.id),
        "name": ticket_type.name,
        "price": str(ticket_type.price),
        "applies_to": ticket_type.applies_to,
        "min_birthdate": (
            str(ticket_type.min_birthdate) if ticket_type.min_birthdate else None
        ),
        "max_birthdate": (
            str(ticket_type.max_birthdate) if ticket_type.max_birthdate else None
        ),
        "kind": ticket_type.kind,
    }


def _resolve_promo_code(*, event, code_str):
    """Resolve and count a submitted promo code string, or return None if
    none was submitted. Must be called inside the same transaction.atomic()
    block as the rest of registration creation, and before the attendee
    loop (so is_hidden ticket-type validation below can see it).

    D1: the max_uses check and the increment are one atomic conditional
    UPDATE (``WHERE uses_count < max_uses``), not a select_for_update()
    held across the rest of registration creation — Postgres serializes two
    concurrent UPDATEs against the same row, so the second one to commit
    re-evaluates the WHERE clause against the first's new count, which is
    exactly what still makes case catalog §5.4(d)'s simultaneous-last-slot
    race resolve to exactly one winner, without holding a lock on a
    popular, unlimited-use code for the duration of an unrelated
    registration's whole write.

    Not-found/inactive/expired/exhausted all raise the same generic
    message, deliberately — a distinguishable error would let someone
    probe for which codes exist.
    """
    code_str = (code_str or "").strip()
    if not code_str:
        return None

    invalid = ValidationError(
        {"promo_code": [_("This promo code is not valid.")]},
        code="invalid_promo_code",
    )
    try:
        promo_code = PromoCode.objects.get(
            event=event, code=code_str.upper(), is_active=True
        )
    except PromoCode.DoesNotExist:
        raise invalid from None

    now = timezone.now()
    if promo_code.valid_from and now < promo_code.valid_from:
        raise invalid
    if promo_code.valid_until and now > promo_code.valid_until:
        raise invalid

    if promo_code.max_uses is not None:
        updated = PromoCode.objects.filter(
            pk=promo_code.pk, uses_count__lt=promo_code.max_uses
        ).update(uses_count=F("uses_count") + 1)
        if not updated:
            raise invalid
    else:
        PromoCode.objects.filter(pk=promo_code.pk).update(
            uses_count=F("uses_count") + 1
        )

    return promo_code


def _validate_ticket_type_for_attendee(
    ticket_type, *, event, attendee, is_child, promo_code
):
    if ticket_type.event_id != event.id or not ticket_type.is_active:
        raise ValidationError(_("Invalid ticket type for this event."))
    if ticket_type.is_hidden:
        unlocked = (
            promo_code is not None
            and promo_code.unlocks_ticket_types.filter(pk=ticket_type.pk).exists()
        )
        if not unlocked:
            # Same generic message as the branch above — a hidden type
            # should look indistinguishable from a nonexistent one.
            raise ValidationError(_("Invalid ticket type for this event."))
    attendee_kind = AppliesTo.CHILD if is_child else AppliesTo.PARENT
    if ticket_type.applies_to not in (attendee_kind, AppliesTo.EITHER):
        raise ValidationError(_("This ticket type isn't available for this attendee."))
    now = timezone.now()
    if ticket_type.available_from and now < ticket_type.available_from:
        raise ValidationError(_("This ticket type isn't available yet."))
    if ticket_type.available_until and now > ticket_type.available_until:
        raise ValidationError(_("This ticket type is no longer available."))
    if is_child:
        birthdate = attendee.birthdate
        too_young = ticket_type.min_birthdate and (
            birthdate is None or birthdate < ticket_type.min_birthdate
        )
        too_old = ticket_type.max_birthdate and (
            birthdate is None or birthdate > ticket_type.max_birthdate
        )
        if too_young or too_old:
            raise ValidationError(
                _("This attendee doesn't meet this ticket type's age requirements.")
            )


def _materialize_ticket(*, attendee, event, ticket_type, registration):
    """Snapshot the ticket type's price onto the ticket at submission time
    (P2: never recomputed afterwards). A session_bundle type materializes
    one SessionTicket per covered session, all sharing this ticket_type —
    see pricing.py::calculate_total for how that avoids double-counting.

    A2: TicketTypeAdminForm.clean() is supposed to stop a session_bundle
    with no sessions attached from ever being saved, but this is the
    belt-and-suspenders backstop for any other path that could produce one
    (a fixture, a data migration, an is_active toggle after its sessions
    were removed) — without it, this loop silently creates zero
    SessionTicket rows and the attendee finishes submit→verify with no
    ticket at all."""
    if ticket_type.kind == TicketType.Kind.SESSION_BUNDLE:
        sessions = list(ticket_type.sessions.all())
        if not sessions:
            logger.error(
                "TicketType %s (%r) is a session_bundle with no sessions "
                "attached — refusing to materialize an empty ticket",
                ticket_type.id,
                ticket_type.name,
            )
            raise ValidationError(_("This ticket type isn't available right now."))
        for session in sessions:
            SessionTicket.objects.create(
                attendee=attendee,
                session=session,
                registration=registration,
                ticket_type=ticket_type,
                price_at_registration=ticket_type.price,
            )
    else:
        EventTicket.objects.create(
            attendee=attendee,
            event=event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=ticket_type.price,
        )


def _attendee_covers_session(*, attendee, registration, session_id):
    if registration.event_tickets.filter(attendee=attendee).exists():
        return True
    return registration.session_tickets.filter(
        attendee=attendee, session_id=session_id
    ).exists()


def _missing_required_extras(
    *, event, registration, attendee, is_child, submitted_extra_ids
):
    """Active Extra.required=True rows (case 3.2's must-choose-one pattern,
    e.g. accommodation) applicable to this attendee that never appear at
    all in what was submitted — distinct from _attach_extra's per-selection
    validation below, which only checks extras that *were* submitted.
    Called after the attendee's ticket is materialized, so session-scoped
    required extras can check coverage via _attendee_covers_session."""
    attendee_kind = "child" if is_child else "parent"
    candidates = Extra.objects.filter(
        event=event, is_active=True, required=True, per_attendee=True
    ).filter(Q(applies_to=attendee_kind) | Q(applies_to="either"))
    missing = []
    for extra in candidates:
        if extra.id in submitted_extra_ids:
            continue
        if extra.session_id is not None and not _attendee_covers_session(
            attendee=attendee, registration=registration, session_id=extra.session_id
        ):
            continue
        missing.append(extra)
    return missing


def _missing_required_registration_extras(*, event, submitted_extra_ids):
    """Same as _missing_required_extras, for per-registration (attendee=None)
    required extras, checked once for the whole booking."""
    candidates = Extra.objects.filter(
        event=event, is_active=True, required=True, per_attendee=False
    )
    return [extra for extra in candidates if extra.id not in submitted_extra_ids]


def _attach_extra(*, registration, attendee, selection, is_child):
    """Validate and materialize one extra selection as a RegistrationExtra.

    ``attendee=None`` means a per-registration extra (a shared cabin). A
    session-scoped extra is required to be per-attendee in this phase —
    "does the whole family cover Saturday" is an ambiguous question this
    plan deliberately doesn't answer; scope a per-registration extra to
    event-wide only.
    """
    extra = selection["extra"]
    choice = selection.get("choice")
    quantity = selection.get("quantity", 1)

    if extra.event_id != registration.event_id or not extra.is_active:
        raise ValidationError(_("Invalid extra for this event."))
    if choice is not None and choice.extra_id != extra.id:
        raise ValidationError(_("Invalid choice for this extra."))
    if extra.requires_choice and choice is None:
        raise ValidationError(_("This extra requires a choice."))
    if extra.per_attendee and attendee is None:
        raise ValidationError(_("This extra must be attached to an attendee."))
    if not extra.per_attendee and attendee is not None:
        raise ValidationError(_("This extra can't be attached to a specific attendee."))
    if quantity > 1 and extra.per_attendee:
        raise ValidationError(
            _(
                "A quantity greater than one is only allowed for per-registration extras."
            )
        )
    if attendee is not None and extra.applies_to != "either":
        attendee_kind = "child" if is_child else "parent"
        if extra.applies_to != attendee_kind:
            raise ValidationError(_("This extra isn't available for this attendee."))
    if extra.session_id is not None:
        if attendee is None:
            raise ValidationError(
                _("A session-scoped extra must be attached to an attendee.")
            )
        if not _attendee_covers_session(
            attendee=attendee, registration=registration, session_id=extra.session_id
        ):
            raise ValidationError(_("This attendee isn't registered for that session."))
    if (
        extra.per_attendee
        and RegistrationExtra.objects.filter(
            registration=registration, extra=extra, attendee=attendee
        ).exists()
    ):
        # Belt-and-suspenders: the DB unique constraint would catch this
        # too, but as an IntegrityError (500), not a clean 400 — check here
        # so a duplicate entry in the submitted payload fails cleanly.
        raise ValidationError(_("This extra is already attached to this attendee."))

    price = extra.price + (choice.price_delta if choice is not None else Decimal("0"))

    if not extra.per_attendee:
        # attendee=None isn't protected by the (registration, extra,
        # attendee) unique constraint's NULL semantics (Postgres treats
        # every NULL as distinct), so a second selection of the same
        # per-registration extra bumps quantity via get_or_create instead
        # of relying on the DB constraint.
        reg_extra, created = RegistrationExtra.objects.get_or_create(
            registration=registration,
            extra=extra,
            attendee=None,
            defaults={
                "choice": choice,
                "quantity": quantity,
                "price_at_registration": price,
            },
        )
        if not created:
            reg_extra.quantity += quantity
            reg_extra.save(update_fields=["quantity"])
    else:
        RegistrationExtra.objects.create(
            registration=registration,
            extra=extra,
            attendee=attendee,
            choice=choice,
            quantity=quantity,
            price_at_registration=price,
        )


def _create_registration(
    *,
    event,
    contact_email,
    last_name,
    parents_data,
    children_data,
    extras_data=(),
    promo_code_str=None,
):
    promo_code = _resolve_promo_code(event=event, code_str=promo_code_str)

    parents_model_data, parent_selections = _split_selections(parents_data)
    children_model_data, child_selections = _split_selections(children_data)

    family, created_parents, created_children = create_family_with_members(
        last_name=last_name,
        parents_data=parents_model_data,
        children_data=children_model_data,
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

    # Itemized pricing only activates once staff have configured at least
    # one active TicketType for this event — otherwise every attendee gets
    # today's flat EventTicket, unchanged (see pricing.py::calculate_total's
    # matching fallback branch).
    itemized = event.ticket_types.filter(is_active=True).exists()

    attendees = [
        (False, parent, selection)
        for parent, selection in zip(created_parents, parent_selections)
    ] + [
        (True, child, selection)
        for child, selection in zip(created_children, child_selections)
    ]

    for is_child, attendee, selection in attendees:
        ticket_type = selection["ticket_type"]
        if itemized:
            if ticket_type is None:
                raise ValidationError(
                    _("Please select a ticket type for every attendee.")
                )
            _validate_ticket_type_for_attendee(
                ticket_type,
                event=event,
                attendee=attendee,
                is_child=is_child,
                promo_code=promo_code,
            )
            _materialize_ticket(
                attendee=attendee,
                event=event,
                ticket_type=ticket_type,
                registration=registration,
            )
        else:
            EventTicket.objects.create(
                attendee=attendee, event=event, registration=registration
            )

        submitted_extra_ids = {sel["extra"].id for sel in selection["extras"]}
        missing_required = _missing_required_extras(
            event=event,
            registration=registration,
            attendee=attendee,
            is_child=is_child,
            submitted_extra_ids=submitted_extra_ids,
        )
        if missing_required:
            raise ValidationError(
                _("Please make a required choice for %(name)s: %(extras)s")
                % {
                    "name": attendee.first_name,
                    "extras": ", ".join(extra.name for extra in missing_required),
                }
            )

        for extra_selection in selection["extras"]:
            _attach_extra(
                registration=registration,
                attendee=attendee,
                selection=extra_selection,
                is_child=is_child,
            )

    missing_required_registration = _missing_required_registration_extras(
        event=event,
        submitted_extra_ids={sel["extra"].id for sel in extras_data},
    )
    if missing_required_registration:
        raise ValidationError(
            _("Please make a required choice: %(extras)s")
            % {
                "extras": ", ".join(
                    extra.name for extra in missing_required_registration
                )
            }
        )

    for extra_selection in extras_data:
        _attach_extra(
            registration=registration,
            attendee=None,
            selection=extra_selection,
            is_child=None,
        )

    if promo_code is not None:
        # Snapshotted once here (P2) — needs the ticket/extra lines above
        # to already exist, and is never recomputed afterwards even if the
        # code is edited later.
        registration.promo_code = promo_code
        registration.discount_amount = calculate_discount(registration, promo_code)
        registration.save(update_fields=["promo_code", "discount_amount"])

    return registration, token


def _resend_verification(registration):
    """Returns (registration, token, was_throttled).

    Deliberately never touches expires_at — a resend gets a fresh token and
    cooldown, but the registration's lifetime stays pinned to its original
    submitted_at + REGISTRATION_TTL_HOURS. Otherwise each resend would push
    the row's expiry out further, letting an attacker who's put a victim's
    address in contact_email keep the row (and the resend cooldown's ~144/
    day email volume) alive indefinitely (A1)."""
    if (
        registration.verification_sent_at is not None
        and timezone.now() - registration.verification_sent_at < RESEND_COOLDOWN
    ):
        return registration, None, True

    token = generate_verification_token()
    registration.verification_token_hash = hash_token(token)
    registration.verification_sent_at = timezone.now()
    registration.save(update_fields=["verification_token_hash", "verification_sent_at"])
    return registration, token, False


@api_view(["GET"])
@permission_classes([AllowAny])
def registration_event_info(request, event_id):
    """
    Public, minimal event lookup for the /register/[eventId] form — just
    enough to render "Register for {name}" without exposing the full
    (staff-authenticated) EventViewSet to anonymous requests. Also carries
    the event's active ticket types/extras (Phase 3) so the form can render
    real choices instead of just a flat price.
    """
    event = get_object_or_404(Event, pk=event_id)

    ticket_types = [
        _ticket_type_payload(ticket_type)
        for ticket_type in event.ticket_types.filter(
            is_active=True, is_hidden=False
        ).order_by("sort_order", "name")
    ]
    extras = [
        {
            "id": str(extra.id),
            "name": extra.name,
            "price": str(extra.price),
            "session_id": str(extra.session_id) if extra.session_id else None,
            "per_attendee": extra.per_attendee,
            "applies_to": extra.applies_to,
            "requires_choice": extra.requires_choice,
            "required": extra.required,
            "default_selected": extra.default_selected,
            "choices": [
                {
                    "id": str(choice.id),
                    "label": choice.label,
                    "price_delta": str(choice.price_delta),
                }
                for choice in extra.choice_rows.filter(is_active=True).order_by(
                    "sort_order", "label"
                )
            ],
        }
        for extra in event.extras.filter(is_active=True).order_by("sort_order", "name")
    ]

    return Response(
        {
            "id": str(event.id),
            "name": event.name,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
            "is_paid": event.is_paid,
            "price": str(event.price) if event.price is not None else None,
            "currency": "SEK",
            "ticket_types": ticket_types,
            "extras": extras,
            "registration_window_status": event.registration_window_status,
            "registration_opens_at": (
                event.registration_opens_at.isoformat()
                if event.registration_opens_at
                else None
            ),
            "registration_closes_at": (
                event.registration_closes_at.isoformat()
                if event.registration_closes_at
                else None
            ),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ValidatePromoCodeThrottle])
def validate_promo_code(request):
    """
    Public, read-only promo-code check for the registration form: lets it
    reveal any is_hidden ticket types the code unlocks (e.g. VIP2026 ->
    Weekend 2026's hidden VIP type) and preview the discount before the
    guardian commits.

    Deliberately advisory only — never locks the PromoCode row or
    increments uses_count (that only happens for real inside
    submit_registration's atomic block via _resolve_promo_code). A code
    that validates here can still fail at submission if its last slot was
    claimed in between; the form should treat this as a preview, not a
    reservation.
    """
    event = get_object_or_404(Event, pk=request.data.get("event"))
    code_str = (request.data.get("code") or "").strip()

    if not code_str:
        return Response({"valid": False})

    try:
        promo_code = PromoCode.objects.get(
            event=event, code=code_str.upper(), is_active=True
        )
    except PromoCode.DoesNotExist:
        return Response({"valid": False})

    now = timezone.now()
    if promo_code.valid_from and now < promo_code.valid_from:
        return Response({"valid": False})
    if promo_code.valid_until and now > promo_code.valid_until:
        return Response({"valid": False})
    if promo_code.max_uses is not None and promo_code.uses_count >= promo_code.max_uses:
        return Response({"valid": False})

    return Response(
        {
            "valid": True,
            "discount_type": promo_code.discount_type,
            "discount_value": str(promo_code.discount_value),
            "applies_to_ticket_type_ids": [
                str(pk)
                for pk in promo_code.applies_to_ticket_types.values_list(
                    "id", flat=True
                )
            ],
            "unlocks_ticket_types": [
                _ticket_type_payload(ticket_type)
                for ticket_type in promo_code.unlocks_ticket_types.filter(
                    is_active=True
                )
            ],
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

    # The frontend gate (hide the form, disable submit in preview mode) is
    # UX only — this is the actual enforcement point. Never trust a client
    # not to POST directly.
    if event.registration_window_status != RegistrationWindowStatus.OPEN:
        raise ValidationError(
            {"event": [_("Registration is not currently open for this event.")]},
            code="registration_not_open",
        )

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
            extras_data=data.get("extras", []),
            promo_code_str=data.get("promo_code"),
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
    at this registration's itemized total (pricing.py::calculate_total): a
    nonzero total routes to pending_payment instead of confirmed, and gets
    a Payment record + payment instructions email instead of a confirmation
    email.
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

    payment = None
    # Paid-ness is a property of this registration's itemized total, not
    # Event.is_paid — a 0kr total (e.g. every attendee on a free/volunteer
    # ticket type) must confirm directly rather than create a Payment row
    # that can never be matched against a bank statement. calculate_total
    # falls back to the flat Event.price for events with no TicketType
    # configured, so this replaces the old event.is_paid check exactly for
    # pre-Phase-3 events too.
    total = calculate_total(registration)

    if email_matches_other_family:
        registration.status = Registration.Status.PENDING_REVIEW
    elif total > 0:
        registration.status = Registration.Status.PENDING_PAYMENT
        registration.expires_at = default_payment_expires_at()
    else:
        registration.status = Registration.Status.CONFIRMED

    registration.verified_at = timezone.now()
    update_fields = ["verified_at", "status"]
    if registration.status == Registration.Status.PENDING_PAYMENT:
        update_fields.append("expires_at")
    registration.save(update_fields=update_fields)

    if total > 0:
        payment = Payment.objects.create(registration=registration, amount=total)

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

    # A Payment row's existence, not Event.is_paid, is the real signal: an
    # itemized event can have a nonzero total (and therefore a Payment row)
    # while Event.price itself is unset (see pricing.py::calculate_total).
    if not hasattr(registration, "payment"):
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
