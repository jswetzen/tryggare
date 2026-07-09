from rest_framework import serializers

from events.models import Event, Extra, ExtraChoice, TicketType
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
        fields = ParentCreateSerializer.Meta.fields + ["ticket_type", "extras"]


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

    def validate(self, data):
        if not data.get("parents") and not data.get("children"):
            raise serializers.ValidationError(
                "A registration needs at least one parent or child"
            )
        return data
