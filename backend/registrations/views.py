import hashlib
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from checkins.audit import log_audit
from config.permissions import POST_REQUIRES_CHANGE, model_permissions
from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
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
    RegistrationIdempotencyKey,
    default_payment_expires_at,
)
from .pricing import calculate_discount, calculate_total
from .serializers import RegistrationSubmitSerializer
from .ticket_rules import validate_ticket_composition
from .services import (
    InvalidPaymentTransition,
    TicketTypeSoldOut,
    confirm_registration_despite_balance,
    mark_payment_paid,
    reserve_ticket_type_capacity,
    sold_counts_for_event,
)
from .swish import payment_instructions
from .tokens import generate_verification_token, hash_token

logger = logging.getLogger(__name__)

# The two check-in-screen money actions (case catalog §9.3). These are the
# money actions a Volontär keeps: handling the family standing in front of
# them, as opposed to browsing everyone's finances.
#
# They are function-based views, so the model has to be named rather than read
# off a queryset, and both are POSTs that modify an *existing* registration —
# mapped to ``change_registration`` rather than DRF's default ``add_``, so the
# grant does not quietly also mean "can conjure registrations out of nothing".
_DOOR_MONEY_PERMISSION = model_permissions(
    Registration, perms_map=POST_REQUIRES_CHANGE, name="DoorMoneyPermissions"
)

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


def _ticket_type_payload(ticket_type, *, sold_count):
    """Shared public JSON shape for a TicketType — used both by
    registration_event_info's normal listing and validate_promo_code's
    unlocked-types payload, so the two never drift apart.

    ``sold_count`` is passed in rather than computed here (R3, gate review
    2026-09-25): both call sites list several ticket types at once, and
    this used to call the single-type count function once per type — an
    N+1 on a public, unauthenticated endpoint. Callers compute the whole
    event's counts in one shot with
    registrations.services.sold_counts_for_event and pass each type's
    share in.

    ``available`` (added 2026-09-24, capacity enforcement increment): a
    plain bool, not a remaining count — see
    registrations.services.ticket_type_sold_count's docstring for what
    "sold" means here. Deliberately not exposing the raw sold count or a
    remaining-seats number: nothing else on this public, unauthenticated
    endpoint reveals how many of anything have sold (prices and age
    windows are configuration, not activity), and "3 left!" is exactly the
    kind of number a competitor or a nosy guardian could poll for over
    time to infer registration velocity. A bool is the minimum a
    guardian's form needs to grey out a full option — matches
    registration_event_info's own "minimal ... without exposing" framing
    for the rest of this payload.
    """
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
        "requires_ticket_type_id": (
            str(ticket_type.requires_ticket_type_id)
            if ticket_type.requires_ticket_type_id
            else None
        ),
        "max_per_required": ticket_type.max_per_required,
        "available": ticket_type.capacity is None or sold_count < ticket_type.capacity,
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

    # "code" is a literal key in the body (not just the ValidationError
    # constructor's own `code=` kwarg, which DRF's default JSONRenderer
    # never serializes) — same pattern as the ticket_sold_out error below,
    # so the frontend can branch on a stable machine-readable value instead
    # of string-matching the translated message.
    invalid = ValidationError(
        {
            "promo_code": [_("This promo code is not valid.")],
            "code": "invalid_promo_code",
        },
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


def _bilingual(en: str, sv: str) -> str:
    """Pick between an EN/SV string by the request's active language.

    Bypasses gettext's catalog lookup on purpose: this deployment's
    django.po has never had `compilemessages` run against it (no gettext
    tools in the image), so every `_("...")` call currently renders English
    regardless of the django_language cookie LocaleMiddleware honors
    correctly — get_language() itself is accurate, only the .mo lookup is
    silently missing. Use this for new user-facing strings that must
    actually be bilingual today; existing `_()` calls elsewhere are a
    pre-existing gap this increment doesn't attempt to fix wholesale.
    """
    return sv if get_language() == "sv" else en


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
    # Age-band check deliberately lives in _child_ticket_age_error, not here:
    # the caller needs this one specific failure reported as a field error
    # keyed to the offending child's index (see _create_registration), not
    # folded into the generic non-field message the rest of this function
    # raises.


def _child_ticket_age_error(ticket_type, birthdate) -> str | None:
    """Returns a bilingual message if `birthdate` falls outside
    `ticket_type`'s configured age band, else None. Split out from
    _validate_ticket_type_for_attendee so the caller can attach it to the
    specific child's index in the response instead of a bare string (a
    banner alone doesn't say *which* of up to six attendees failed)."""
    too_young = ticket_type.min_birthdate and (
        birthdate is None or birthdate < ticket_type.min_birthdate
    )
    too_old = ticket_type.max_birthdate and (
        birthdate is None or birthdate > ticket_type.max_birthdate
    )
    if too_young or too_old:
        return _bilingual(
            "This attendee doesn't meet this ticket type's age requirements.",
            "Barnet uppfyller inte åldersgränsen för den valda biljettypen.",
        )
    return None


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
        # of relying on the DB constraint. `choice` is part of the lookup,
        # not just the defaults — two selections of the same extra with
        # different choices (e.g. "Large cabin" vs "Small cabin") are
        # different line items, each with their own snapshotted price, not
        # one row whose quantity happens to grow.
        reg_extra, created = RegistrationExtra.objects.get_or_create(
            registration=registration,
            extra=extra,
            attendee=None,
            choice=choice,
            defaults={
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

    # Per-kind position within the frontend's own parents[]/children[]
    # arrays (not the combined `attendees` list below) — this is what lets
    # a field error point at the exact row the guardian needs to fix
    # (see the age-band ValidationError just below).
    child_index = 0

    # Pass 1: validate every attendee's ticket-type selection (existence,
    # eligibility, age band) — read-only, no writes, no locks. Split out
    # from materialization (pass 2 below) so capacity can be checked for
    # the *whole registration* in one batch between the two passes — see
    # that batch's own comment (R1, gate review 2026-09-25) for why a
    # single deterministic-order lock replaced locking one TicketType row
    # per attendee as this loop reached it.
    if itemized:
        for is_child, _attendee, selection in attendees:
            ticket_type = selection["ticket_type"]
            if ticket_type is None:
                if not is_child:
                    # "Guardian only" (owner decision eb5d26f4): an adult
                    # with no ticket_type is accepted as a guardian of the
                    # registration's children but holds no ticket -- no
                    # eligibility check, no seat, no price line. Children
                    # always need a ticket, so they still fall through to
                    # the error below.
                    continue
                raise ValidationError(
                    _("Please select a ticket type for every attendee.")
                )
            _validate_ticket_type_for_attendee(
                ticket_type,
                event=event,
                attendee=_attendee,
                is_child=is_child,
                promo_code=promo_code,
            )
            if is_child:
                age_error = _child_ticket_age_error(ticket_type, _attendee.birthdate)
                if age_error:
                    raise ValidationError({"children": {str(child_index): [age_error]}})
                child_index += 1

        # A registration in which nobody holds a ticket (an adults-only
        # submission where every adult is "guardian only") would confirm at
        # 0 kr with no seat and no line item -- nothing to attend. Children
        # can't reach this (they always carry a ticket), so this only ever
        # catches the adults-only case.
        if all(selection["ticket_type"] is None for _c, _a, selection in attendees):
            raise ValidationError(_("Please select a ticket type for every attendee."))

        # Batch capacity lock+check (R1, gate review 2026-09-25 — replaces
        # the per-attendee select_for_update this increment shipped with
        # originally, which the verifier reproduced deadlocking in 5/6
        # opposite-order pairs: two registrations each picking the same two
        # capacity-limited types in opposite order would lock them in
        # opposite order too, the textbook Postgres deadlock shape).
        # `needed` is per-attendee, not per-materialized-row — a
        # session_bundle attendee still needs exactly one seat no matter
        # how many sessions their type bundles (see
        # reserve_ticket_type_capacity's own docstring).
        needed_by_ticket_type: dict = {}
        for _is_child, _attendee, selection in attendees:
            ticket_type = selection["ticket_type"]
            if ticket_type is None:
                continue  # guardian only: consumes no seat
            needed_by_ticket_type[ticket_type] = (
                needed_by_ticket_type.get(ticket_type, 0) + 1
            )
        try:
            reserve_ticket_type_capacity(needed_by_ticket_type)
        except TicketTypeSoldOut as exc:
            raise ValidationError(
                {
                    "ticket_type": [
                        _bilingual(
                            f'"{exc.ticket_type.name}" is sold out.',
                            f'"{exc.ticket_type.name}" är fullbokad.',
                        )
                    ],
                    "code": "ticket_sold_out",
                }
            ) from exc

    # Pass 2: materialize tickets/extras now that every selection in this
    # registration is known to be valid and to fit within capacity.
    parent_index = 0
    for is_child, attendee, selection in attendees:
        ticket_type = selection["ticket_type"]
        if itemized and ticket_type is None:
            # Guardian-only adult (pass 1 already rejected a ticketless
            # child). No ticket, so nothing per-attendee can attach to them:
            # a per-attendee extra would be a priced line for someone who
            # isn't attending, and required per-attendee extras don't apply.
            # Refuse a submitted extra loudly rather than dropping it, so a
            # guardian never believes they bought something they didn't.
            if selection["extras"]:
                raise ValidationError(
                    {
                        "parents": {
                            str(parent_index): [
                                _(
                                    "Extras can only be added for an adult with a ticket."
                                )
                            ]
                        }
                    }
                )
            parent_index += 1
            continue
        if not is_child:
            parent_index += 1
        if itemized:
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

    validate_ticket_composition(registration)

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

    # One bulk query pair for the whole event (R3, gate review
    # 2026-09-25), not one _ticket_type_payload-internal query per ticket
    # type rendered below — see sold_counts_for_event's own docstring.
    sold_counts = sold_counts_for_event(event)
    active_ticket_types = event.ticket_types.filter(is_active=True)
    ticket_types = [
        _ticket_type_payload(
            ticket_type, sold_count=sold_counts.get(str(ticket_type.id), 0)
        )
        for ticket_type in active_ticket_types.filter(is_hidden=False).order_by(
            "sort_order", "name"
        )
    ]
    # A code-only, invite-only event (every active TicketType hidden) would
    # otherwise leave the form with an empty ticket_types list and no visible
    # promo-code box to unlock any — this tells the frontend to show the box
    # anyway so there's a way in.
    has_hidden_ticket_types = active_ticket_types.filter(is_hidden=True).exists()
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
                for choice in extra.choice_rows.all()
            ],
        }
        for extra in event.extras.filter(is_active=True)
        .order_by("sort_order", "name")
        .prefetch_related(
            Prefetch(
                "choice_rows",
                queryset=ExtraChoice.objects.filter(is_active=True).order_by(
                    "sort_order", "label"
                ),
            )
        )
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
            "header_image_url": event.header_image_url or None,
            "accent_color": event.accent_color or None,
            "ticket_types": ticket_types,
            "has_hidden_ticket_types": has_hidden_ticket_types,
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

    # Same bulk-query rationale as registration_event_info above — a
    # promo code can unlock several hidden ticket types at once (R3, gate
    # review 2026-09-25).
    sold_counts = sold_counts_for_event(event)
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
                _ticket_type_payload(
                    ticket_type, sold_count=sold_counts.get(str(ticket_type.id), 0)
                )
                for ticket_type in promo_code.unlocks_ticket_types.filter(
                    is_active=True
                )
            ],
        }
    )


# How long an idempotency-key reservation can sit unfinished before it's
# treated as abandoned rather than "still in progress" — see
# _reserve_idempotency_key's docstring (P2, added 2026-09-24 after gate
# review) for why this exists at all: without it, a worker that dies
# mid-request (killed process, rescheduled pod) between reserving a key and
# filling in its response would leave every future retry under that key
# stuck on a 409 forever, since nothing else ever completes the reservation.
# 60s is generous for this endpoint's own work (a single DB transaction plus
# one best-effort email send, see _execute_submit_registration) while still
# being short enough that a guardian who retries a couple of times inside a
# minute never races a reclaim against their own still-healthy request.
STALE_RESERVATION_AGE = timedelta(seconds=60)


def _idempotency_fingerprint(raw_payload) -> str:
    """SHA-256 of the raw submitted JSON body, minus the idempotency key
    itself (that's the lookup key, not part of what has to match) and with
    dict keys sorted so the hash is stable regardless of field-insertion
    order — the frontend always sends the same shape, but nothing enforces
    that, and a non-canonical hash would make a byte-identical retry fail
    to match itself purely over key ordering.

    Hashes ``request.data`` (already-parsed JSON, plain dicts/lists/
    scalars) rather than the serializer's ``validated_data`` on purpose:
    validated_data has PrimaryKeyRelatedField values resolved to model
    instances (Event, TicketType, Extra, ExtraChoice...), which aren't
    JSON-serializable without extra plumbing, and comparing the raw wire
    payload is exactly "was this the same request" anyway — the whole point
    here, unlike validation, isn't to interpret the payload, just to tell
    two submissions apart byte-for-byte.
    """
    if isinstance(raw_payload, dict):
        canonical = {k: v for k, v in raw_payload.items() if k != "idempotency_key"}
    else:
        canonical = raw_payload
    encoded = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _execute_submit_registration(request, data):
    """The actual submission logic: validated payload in, ``(response
    body, HTTP status, Registration-or-None)`` out.

    Split out of ``submit_registration`` on 2026-09-24 so the idempotency-
    key wrapper below (see ``RegistrationIdempotencyKey``) can cache
    exactly what this function returns without duplicating the honeypot/
    window/dedup/create logic, and so the wrapper can tell "raised before
    reaching a persisted outcome" (nothing to cache, safe to retry under
    the same key once the caller fixes whatever was wrong) apart from
    "returned a real result" (cache it) purely from whether this function
    returns normally or raises. Every branch is unchanged from before the
    split — this is a pure extraction, not a behavior change for a request
    with no idempotency key.
    """
    # Honeypot: real guardians never fill this hidden field. Respond as if
    # successful — bots shouldn't learn their submission was rejected —
    # without persisting anything.
    if data.get("website"):
        logger.warning("Registration honeypot triggered for event %s", data["event"].id)
        return (
            {
                "reference_code": None,
                "message": _("Thanks — check your email to confirm."),
            },
            status.HTTP_201_CREATED,
            None,
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
            contact_email__iexact=contact_email,
            status=Registration.Status.PENDING_VERIFICATION,
        )
        .order_by("-submitted_at")
        .first()
    )

    if existing is not None and not existing.is_expired:
        # This branch is deliberately reached by two different callers with
        # different intent, and the response has to serve both:
        #   - the confirmation screen's explicit "resend" action (handleResend
        #     in +page.svelte), which sends this exact payload back on
        #     purpose and treats any 2xx as "an email is on its way" — that
        #     flow already shipped and must not break.
        #   - a guardian who used "Edit and resend" (or just double-submitted)
        #     with genuinely *changed* form data — before this "code" field
        #     existed, that resubmit silently hit this same branch, the new
        #     data was discarded, and the guardian saw the ordinary success
        #     screen with no indication anything was dropped (2026-09-28
        #     incident, knowitall 6d4f0964).
        # The status codes stay exactly what they were (200 throttled / 201
        # resent) rather than moving to a 4xx like idempotency_conflict's —
        # a 4xx would land in submitPayload's catch block and also break
        # handleResend, which has no code-check and just wants the request to
        # succeed. Instead "code": "registration_already_pending" rides
        # alongside the existing 2xx body so submitPayload's *success* path
        # can recognize the dedup happened and show a dedicated "not saved"
        # state, while handleResend keeps ignoring it and working exactly as
        # before.
        registration, token, throttled = _resend_verification(existing)
        if throttled:
            return (
                {
                    "reference_code": registration.reference_code,
                    "code": "registration_already_pending",
                    "message": _(
                        "A registration for this email is already waiting "
                        "for confirmation. We can't resend so soon — please "
                        "use the confirmation email already sent. Any "
                        "changes you just made were not saved."
                    ),
                },
                status.HTTP_200_OK,
                registration,
            )
        email_sent = send_verification_email(registration, token)
        log_audit(
            request,
            action="registration_resent",
            entity_type="Registration",
            entity_id=str(registration.id),
            details={"reference_code": registration.reference_code},
        )
        return (
            {
                "reference_code": registration.reference_code,
                "code": "registration_already_pending",
                # False means the registration is stored but the mail didn't
                # go out (see emails.py::_send_or_degrade) — the client says
                # so plainly and offers the resend action rather than
                # claiming an email is on its way.
                "email_sent": email_sent,
                "message": _(
                    "A registration for this email is already waiting for "
                    "confirmation. We've sent a fresh confirmation email — "
                    "any changes you just made were not saved."
                ),
            },
            status.HTTP_201_CREATED,
            registration,
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

    email_sent = send_verification_email(registration, token)

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

    return (
        {
            "reference_code": registration.reference_code,
            "email_sent": email_sent,
            "message": _("Thanks — check your email to confirm."),
        },
        status.HTTP_201_CREATED,
        registration,
    )


def _idempotency_replay_or_conflict_response(existing_key, fingerprint):
    """Given a RegistrationIdempotencyKey this request did NOT win the
    reservation for, decide what to hand back: the winner's cached response
    (a true replay), a hard conflict (the same key reused for a genuinely
    different payload), or "still working on it" (the winner reserved the
    key but hasn't finished yet). Shared by _reserve_idempotency_key's
    first-collision path and its post-reclaim-attempt path below, so a
    losing request is resolved identically either way.

    Both conflict shapes carry a machine-readable ``code`` (P1, added
    2026-09-24 after gate review) alongside the existing translated
    message/details — the frontend needs to tell "same key, different
    payload" apart from "still processing" *before* it falls back to
    extractErrorMessage's generic first-string-in-the-body heuristic, which
    would otherwise have no way to distinguish them (see
    handleSubmit's catch block).
    """
    if existing_key.request_fingerprint != fingerprint:
        # Same key, different payload: either a client bug (the key didn't
        # get reset when it should have — see the frontend's "starts a new
        # registration resets the key" rule) or an attempt to read back a
        # response that was never this caller's. Either way, silently
        # returning the other payload's result would be actively wrong, so
        # this is a hard conflict, not a replay.
        return Response(
            {
                "idempotency_key": [
                    _(
                        "This idempotency key was already used for a "
                        "different submission."
                    )
                ],
                "code": "idempotency_conflict",
            },
            status=status.HTTP_409_CONFLICT,
        )
    if existing_key.response_body is None:
        # The reservation exists but the request that made it hasn't
        # finished yet — the losing side of the exact race the reservation
        # exists to prevent. There is no result to replay yet; asking the
        # caller to retry is honest, returning a guessed result would not
        # be.
        return _idempotency_in_progress_response()
    return Response(existing_key.response_body, status=existing_key.response_status)


def _idempotency_in_progress_response():
    """The "try again shortly" 409 — factored out because
    _reserve_idempotency_key also reaches for it when a concurrent
    reclaimer's DELETE-then-INSERT leaves a real, narrow gap where the row
    genuinely doesn't exist for a moment (see that function's ``except
    RegistrationIdempotencyKey.DoesNotExist`` handling): that gap is a
    finer-grained instance of "someone else is mid-flight on this key",
    exactly what this response already says, so there is no separate
    message to maintain for it.
    """
    return Response(
        {
            "error": _(
                "This submission is already being processed — "
                "please try again in a moment."
            ),
            "code": "idempotency_in_progress",
        },
        status=status.HTTP_409_CONFLICT,
    )


def _reserve_idempotency_key(*, key, event, fingerprint):
    """Reserves ``key`` for this request, or resolves a request that lost
    the reservation race. Returns either a RegistrationIdempotencyKey (this
    request won and must run the real work, then fill it in) or a Response
    (this request lost — the Response is the final answer).

    Reserving the row *before* doing any real work — not a plain
    check-then-insert — is what closes the concurrent-request race: two
    requests arriving within microseconds of each other both see "no row
    yet" under a SELECT, but only one INSERT can win the unique constraint
    on ``key``; the other raises IntegrityError.

    The reclaim step (P2, added 2026-09-24 after gate review) handles the
    case where the *winner* of that race never gets to finish: a worker
    killed mid-request, a rescheduled pod, any hard process death between
    reserving the key and filling in response_body. Without it, every
    future retry under that key would see "already being processed"
    forever, since nothing else was ever going to complete the reservation.
    A reservation unfinished for longer than STALE_RESERVATION_AGE is
    reclaimed: deleted via a *conditional* delete (matched on pk +
    still-unfinished + still-stale, so two requests reclaiming at the same
    instant can't both succeed) and re-reserved for this request. Deletion
    uses the model's existing ``created_at`` — no new field, no migration.

    Per the reviewed plan, the reclaim is attempted at most once: if the
    conditional delete matches nothing (someone else already reclaimed, or
    the original request finished, between our read and our delete) or the
    retried INSERT itself loses a fresh race, this falls through to
    resolving normally against whatever is there now — replay, conflict, or
    "still in progress" — rather than looping. That keeps this function's
    worst case bounded (at most two INSERT attempts) instead of risking a
    request retrying indefinitely against a key under contention.

    Both re-reads below tolerate the row having vanished entirely
    (RegistrationIdempotencyKey.DoesNotExist) rather than letting that
    propagate as a 500. This is a real, narrow possibility, not defensive
    overkill: a reclaim is a DELETE followed by a *separate*, later INSERT
    statement — nothing makes that pair atomic against a concurrent
    reader — so a second request racing the same reclaim can legitimately
    read in the gap between "the stale row is gone" and "the reclaiming
    request's new row exists yet". A multi-threaded, two-real-connections
    test (IdempotencyKeyStaleReclaimRaceTests in tests_idempotency.py) is
    what caught this — a single-connection mocked IntegrityError can't
    reproduce it, since mocking can only fake a collision at a call
    boundary, not an genuinely empty moment between two separate
    statements on another connection.
    """
    try:
        with transaction.atomic():
            return RegistrationIdempotencyKey.objects.create(
                key=key, event=event, request_fingerprint=fingerprint
            )
    except IntegrityError:
        pass

    try:
        existing_key = RegistrationIdempotencyKey.objects.get(key=key)
    except RegistrationIdempotencyKey.DoesNotExist:
        return _idempotency_in_progress_response()

    cutoff = timezone.now() - STALE_RESERVATION_AGE
    if existing_key.response_body is None and existing_key.created_at < cutoff:
        deleted_count, _unused = RegistrationIdempotencyKey.objects.filter(
            pk=existing_key.pk,
            response_body__isnull=True,
            created_at__lt=cutoff,
        ).delete()
        if deleted_count:
            try:
                with transaction.atomic():
                    return RegistrationIdempotencyKey.objects.create(
                        key=key, event=event, request_fingerprint=fingerprint
                    )
            except IntegrityError:
                # Another request reserved (or reclaimed) the same key in
                # the instant between our delete and our retry — re-read
                # and resolve against that below, rather than reclaiming
                # again (see the "at most once" note above).
                pass
        # Either the conditional delete matched nothing (someone else
        # already reclaimed, or the original request finished, first) or
        # our own post-reclaim retry just lost a fresh race — re-read
        # current state either way.
        try:
            existing_key = RegistrationIdempotencyKey.objects.get(key=key)
        except RegistrationIdempotencyKey.DoesNotExist:
            return _idempotency_in_progress_response()

    return _idempotency_replay_or_conflict_response(existing_key, fingerprint)


# Postgres error codes (SQLSTATE) for the two conflicts
# reserve_ticket_type_capacity's single deterministic-order lock is meant to
# make unreachable for *its own* lock ordering, but that lock is not the
# only thing this transaction can collide with — some other, unrelated
# ordering elsewhere (or Postgres's SERIALIZABLE machinery, if that
# isolation level is ever turned on) can still legitimately abort one side.
# 40P01 = deadlock_detected, 40001 = serialization_failure. See
# _submit_registration_or_busy's own docstring for why both are handled
# identically here (both mean "retry the whole request, nothing was your
# fault").
_DEADLOCK_PGCODES = frozenset({"40P01", "40001"})


def _is_deadlock_or_serialization_failure(exc: OperationalError) -> bool:
    """Django wraps the DB-API driver's own exception (psycopg's
    OperationalError subclasses, e.g. ``errors.DeadlockDetected``) as
    ``django.db.OperationalError`` with the original attached as
    ``__cause__`` — that original carries the real Postgres SQLSTATE in
    ``.pgcode``. Checking the code, not the exception class or message
    text, is deliberate: psycopg raises several different
    OperationalError subclasses for unrelated conditions (a dropped
    connection, a statement timeout, ...) that must NOT be swallowed into
    a misleading "try again" response — only these two specific,
    inherently-transient conflicts should ever be.
    """
    return getattr(exc.__cause__, "pgcode", None) in _DEADLOCK_PGCODES


def _registration_busy_response():
    """The 503 a deadlock/serialization failure resolves to — R1, gate
    review 2026-09-25, added after a live verifier reproduced a bare 500 in
    5/6 opposite-order pairs before reserve_ticket_type_capacity's
    single-lock fix. Even with that fix, Postgres can still detect and
    abort a genuine conflict between this transaction and some other one;
    the guardian did nothing wrong, so this is a clean, retryable 503 with
    a machine-readable code, not a 500 that looks like a bug.
    """
    return Response(
        {
            "error": _bilingual(
                "Many people are registering right now — please try again.",
                "Många anmäler sig just nu — försök igen om en liten stund.",
            ),
            "code": "registration_busy_retry",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _submit_registration_or_busy(request, data):
    """Runs _execute_submit_registration, translating a Postgres deadlock
    or serialization failure into ``_registration_busy_response()`` instead
    of letting it propagate as an unhandled 500.

    Returns either the normal ``(body, status, registration)`` tuple, or a
    Response standing in for "the database was too busy, try again" —
    mirrors ``_reserve_idempotency_key``'s own Response-or-real-value
    convention above, for the same reason: the caller tells the two apart
    with a single ``isinstance(result, Response)`` check instead of a
    second exception type.

    Shared by both of submit_registration's branches (with and without an
    idempotency key) so the deadlock/serialization-failure handling exists
    in exactly one place — R1, gate review 2026-09-25. Every other
    exception (ValidationError from a rejected submission,
    ticket_sold_out, any other OperationalError that isn't one of these
    two specific codes, ...) is deliberately left to propagate unchanged;
    this function only ever intercepts the one thing it names.
    """
    try:
        return _execute_submit_registration(request, data)
    except OperationalError as exc:
        if not _is_deadlock_or_serialization_failure(exc):
            raise
        logger.warning(
            "Registration submission hit a deadlock/serialization failure "
            "(pgcode=%s) — returning 503 for the client to retry",
            getattr(exc.__cause__, "pgcode", None),
        )
        return _registration_busy_response()


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
    creating a duplicate row — see _execute_submit_registration.

    Idempotency (added 2026-09-24, see RegistrationIdempotencyKey for the
    full reasoning): an optional client-supplied ``idempotency_key`` makes a
    retried POST — network failure, a double submit that slips past the
    frontend's own in-flight guard, a stale tab resubmitting — replay the
    exact original response instead of running _execute_submit_registration
    a second time, so nothing gets created (or resent, or emailed) twice.
    Blank/omitted key: every branch below is skipped and this behaves
    exactly as it did before this key existed.

    Both branches below route the actual work through
    _submit_registration_or_busy rather than calling
    _execute_submit_registration directly, so a Postgres deadlock or
    serialization failure (R1, gate review 2026-09-25) is caught
    identically either way — see that helper's own docstring.
    """
    serializer = RegistrationSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    idempotency_key = (data.get("idempotency_key") or "").strip()
    if not idempotency_key:
        result = _submit_registration_or_busy(request, data)
        if isinstance(result, Response):
            return result
        body, response_status, _registration = result
        return Response(body, status=response_status)

    fingerprint = _idempotency_fingerprint(request.data)

    reservation = _reserve_idempotency_key(
        key=idempotency_key, event=data.get("event"), fingerprint=fingerprint
    )
    if isinstance(reservation, Response):
        # This request lost the reservation (a true replay, a hard
        # conflict, or "still in progress") — _reserve_idempotency_key
        # already built the final answer; nothing below has anything left
        # to do.
        return reservation
    key_record = reservation

    try:
        result = _submit_registration_or_busy(request, data)
    except Exception:
        # Nothing persisted under this key (the registration-creation
        # transaction, if entered at all, already rolled back on its own).
        # Delete the reservation so a retry with a corrected payload under
        # the *same* key — e.g. the guardian fixes a ticket-eligibility
        # error the client-side checks didn't catch and resubmits — is a
        # fresh attempt, not a permanent 409 against a reservation that
        # will never complete. See RegistrationIdempotencyKey's docstring.
        key_record.delete()
        raise

    if isinstance(result, Response):
        # The database was too busy (deadlock/serialization failure) —
        # same reservation-cleanup reasoning as the except-block above:
        # nothing persisted under this key, so a retry (the 503 is
        # explicitly asking the caller to do exactly that) must not find a
        # permanent reservation blocking it.
        key_record.delete()
        return result

    body, response_status, registration = result
    key_record.response_status = response_status
    key_record.response_body = body
    key_record.registration = registration
    key_record.save(update_fields=["response_status", "response_body", "registration"])

    return Response(body, status=response_status)


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
            email__iexact=registration.contact_email, anonymized_at__isnull=True
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

    email_sent = True
    if registration.status == Registration.Status.CONFIRMED:
        email_sent = send_confirmation_email(registration)
    elif registration.status == Registration.Status.PENDING_PAYMENT:
        email_sent = send_payment_instructions_email(registration)

    response_data = {
        "status": registration.status,
        "reference_code": registration.reference_code,
        "event_name": registration.event.name,
        # The verification itself has already committed regardless — this
        # only says whether the follow-up mail (confirmation, or payment
        # instructions) actually left. See emails.py::_send_or_degrade.
        "email_sent": email_sent,
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


@api_view(["POST"])
@permission_classes([_DOOR_MONEY_PERMISSION])
def mark_registration_paid(request, registration_id):
    """Check-in screen's "ta betalt nu" action (case catalog §9.3): a family
    with a pending_payment registration is at the front of the check-in
    queue, pays on the spot, and staff clear the gate right there — one
    screen, no admin round-trip. Records the full outstanding balance as
    received, same as the Django admin's mark-paid actions
    (RegistrationAdmin/PaymentAdmin), just reachable from the check-in UI.
    """
    method = request.data.get("method", "")
    if method not in Payment.Method.values:
        return Response(
            {"error": _("Unknown payment method")}, status=status.HTTP_400_BAD_REQUEST
        )

    registration = get_object_or_404(
        Registration.objects.select_related("payment"), pk=registration_id
    )
    payment = getattr(registration, "payment", None)
    if payment is None:
        return Response(
            {"error": _("Registration has no payment")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        mark_payment_paid(payment, method=method, marked_by=request.user)
    except InvalidPaymentTransition as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    # mark_payment_paid mutates payment.registration, not necessarily the
    # same Python object as the `registration` fetched above — re-read
    # rather than assume the in-memory instance was updated in place.
    registration.refresh_from_db()

    log_audit(
        request,
        action="registration_payment_marked_paid",
        entity_type="Registration",
        entity_id=str(registration.id),
        details={
            "reference_code": registration.reference_code,
            "method": method,
            "amount": str(payment.amount),
            "source": "checkin_ui",
        },
    )

    return Response(
        {"status": registration.status, "reference_code": registration.reference_code}
    )


@api_view(["POST"])
@permission_classes([_DOOR_MONEY_PERMISSION])
def confirm_registration_despite_balance_view(request, registration_id):
    """Check-in screen's "släpp in, lös betalning senare" override (case
    catalog §9.3): a deliberate staff judgment call to let a family in
    without full payment, independently audited from money actually
    arriving — see confirm_registration_despite_balance's own docstring.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("payment"), pk=registration_id
    )

    try:
        confirm_registration_despite_balance(registration, confirmed_by=request.user)
    except InvalidPaymentTransition as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    log_audit(
        request,
        action="registration_confirmed_despite_balance",
        entity_type="Registration",
        entity_id=str(registration.id),
        details={
            "reference_code": registration.reference_code,
            "source": "checkin_ui",
        },
    )

    return Response(
        {"status": registration.status, "reference_code": registration.reference_code}
    )
