from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from events.models import Event, Extra, ExtraChoice, TicketType
from families.models import Parent
from families.serializers import ChildCreateSerializer, ParentCreateSerializer


class ExtraSelectionSerializer(serializers.Serializer):
    """One extra selection: which Extra, an optional ExtraChoice, and a
    quantity. Whether a given quantity/choice combination is actually valid
    for this Extra (e.g. quantity>1 only for a per-registration extra,
    choice required when Extra.requires_choice) depends on the Extra's own
    flags and can't be checked at the field level here — see
    views.py::_create_registration, which validates against the actual
    Extra/TicketType rows for the submitted event.
    """

    extra = serializers.PrimaryKeyRelatedField(
        queryset=Extra.objects.filter(is_active=True)
    )
    choice = serializers.PrimaryKeyRelatedField(
        queryset=ExtraChoice.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        default=None,
    )
    quantity = serializers.IntegerField(default=1, min_value=1)


class RegistrationParentSerializer(ParentCreateSerializer):
    """ParentCreateSerializer plus the registration-only ticket
    type/extras selections. A subclass rather than an edit to
    families/serializers.py directly, so the shared staff AddFamilyPanel
    flow (which has no ticket-type concept) stays untouched."""

    # Phone is mandatory for every adult on a public registration, ticketed
    # or not (owner decision eb5d26f4, child safety: any adult on the
    # registration is a guardian of all its children, so staff must be able
    # to reach every one of them). Declared here rather than on
    # ParentCreateSerializer so the staff AddFamilyPanel flow, where a phone
    # is optional, is untouched. Enforced at field level (not in the
    # top-level validate()) so a missing phone comes back in DRF's native
    # per-row shape -- {"parents": [{}, {"phone": [msg]}]} -- and is
    # reported together with any other field errors in one round trip.
    phone = serializers.CharField(
        max_length=50,
        error_messages={
            "required": _("A phone number is required for every adult."),
            "blank": _("A phone number is required for every adult."),
            "null": _("A phone number is required for every adult."),
        },
    )
    # "Guardian only" (owner decisions eb5d26f4, d9245e21): a responsible
    # adult who is NOT attending -- no ticket, no seat, no charge, no health
    # information. On an itemized event (>= 1 active TicketType) a null/omitted
    # ``ticket_type`` already means that; there is no ticket to pick "none"
    # of on a flat-price event, so ``guardian_only: true`` is the explicit way
    # to say it there (and is accepted, redundantly, on an itemized event as
    # long as no ticket_type is also given). RegistrationSubmitSerializer.validate
    # normalizes this to the effective value, so everything downstream reads
    # one flag.
    guardian_only = serializers.BooleanField(required=False, default=False)
    ticket_type = serializers.PrimaryKeyRelatedField(
        queryset=TicketType.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        default=None,
    )
    extras = ExtraSelectionSerializer(many=True, required=False, default=list)

    class Meta(ParentCreateSerializer.Meta):
        # DRF's ModelSerializer requires every declared field to be listed
        # in Meta.fields — a subclass doesn't inherit its parent's list
        # automatically extended, only the same list, so ticket_type/extras
        # must be added explicitly here.
        fields = ParentCreateSerializer.Meta.fields + [
            "ticket_type",
            "extras",
            "guardian_only",
        ]


class RegistrationChildSerializer(ChildCreateSerializer):
    """ChildCreateSerializer plus the registration-only ticket
    type/extras selections — see RegistrationParentSerializer."""

    ticket_type = serializers.PrimaryKeyRelatedField(
        queryset=TicketType.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        default=None,
    )
    extras = ExtraSelectionSerializer(many=True, required=False, default=list)

    class Meta(ChildCreateSerializer.Meta):
        fields = ChildCreateSerializer.Meta.fields + ["ticket_type", "extras"]


class RegistrationSubmitSerializer(serializers.Serializer):
    """Public submission payload: an event plus the same nested
    parents/children shape the staff AddFamilyPanel flow already uses (via
    the same ParentCreateSerializer/ChildCreateSerializer, extended above
    with ticket_type/extras), so consent capture and health-text validation
    get identical server-side rigor.
    """

    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    last_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    contact_email = serializers.EmailField()
    parents = RegistrationParentSerializer(many=True, required=False, default=list)
    children = RegistrationChildSerializer(many=True, required=False, default=list)
    # Per-registration extras (attendee=None) — a shared cabin, a parking
    # pass with quantity > 1. Distinct from parents[*]/children[*].extras,
    # which are per-attendee.
    extras = ExtraSelectionSerializer(many=True, required=False, default=list)
    # Resolved/locked/validated in views.py::_resolve_promo_code, not here
    # — a plain string field, since "not a valid code" needs the single
    # generic error message that function raises, not a PrimaryKeyRelated
    # field's distinguishable "object does not exist" error.
    promo_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    # Honeypot: hidden on the real form via CSS; real guardians never fill
    # this in, bots filling every field typically do.
    website = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=False
    )
    # Optional, client-generated (crypto.randomUUID() at form mount — see
    # register/[eventId]/+page.svelte) — added 2026-09-24 so a retried POST
    # (network failure, a double submit that slips past the frontend's own
    # in-flight guard) replays the original response instead of creating a
    # second registration. Omitted entirely, behavior is unchanged — see
    # views.py::submit_registration's idempotency handling, which is a
    # no-op when this is blank.
    idempotency_key = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        if not data.get("parents") and not data.get("children"):
            raise serializers.ValidationError(
                _("A registration needs at least one parent or child")
            )
        # Owner decision eb5d26f4: a guardian is required only when there are
        # children. Every adult on the registration is a guardian of all its
        # children (no per-child link), and needn't hold a ticket. Keyed under
        # "parents" (a plain list of messages, not per-row) so the client can
        # hang it on the first-parent row; per-row phone errors arrive in the
        # field-level shape instead, see RegistrationParentSerializer.phone.
        if data.get("children") and not data.get("parents"):
            raise serializers.ValidationError(
                {
                    "parents": [
                        _(
                            "A registration with children needs at least one "
                            "adult who is their guardian."
                        )
                    ]
                }
            )

        # Resolve who is a guardian-only adult and police what that implies.
        # Per-row errors use DRF's native list-of-dicts shape (like phone), so
        # a client keyed on the row index can attach them to the right field.
        itemized = data["event"].ticket_types.filter(is_active=True).exists()
        row_errors = []
        any_error = False
        for parent in data.get("parents", []):
            errors = {}
            ticket_type = parent.get("ticket_type")
            explicit = parent.get("guardian_only", False)
            if explicit and itemized and ticket_type is not None:
                errors["ticket_type"] = [
                    _("A guardian who isn't attending can't also choose a ticket.")
                ]
            guardian_only = explicit or (itemized and ticket_type is None)
            parent["guardian_only"] = guardian_only
            if guardian_only and (
                parent.get("health_consent_status")
                != Parent.HealthConsentStatus.NOT_APPLICABLE
            ):
                # Rejected rather than silently dropped: a guardian-only
                # adult is not asked per-attendee questions, so a client that
                # sends health information is out of step with the form and
                # should hear about it instead of the data quietly vanishing
                # (ParentCreateSerializer.validate has already blanked
                # allergies/notes unless consent was granted, so the consent
                # status is the one field that tells us).
                errors["health_consent_status"] = [
                    _(
                        "Health information can't be recorded for a guardian "
                        "who isn't attending."
                    )
                ]
            any_error = any_error or bool(errors)
            row_errors.append(errors)
        if any_error:
            raise serializers.ValidationError({"parents": row_errors})
        return data
