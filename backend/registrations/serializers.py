from rest_framework import serializers

from events.models import Event
from families.serializers import ChildCreateSerializer, ParentCreateSerializer


class RegistrationSubmitSerializer(serializers.Serializer):
    """Public submission payload: an event plus the same nested
    parents/children shape the staff AddFamilyPanel flow already uses (via
    the same ParentCreateSerializer/ChildCreateSerializer), so consent
    capture and health-text validation get identical server-side rigor.
    """

    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    last_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    contact_email = serializers.EmailField()
    parents = ParentCreateSerializer(many=True, required=False, default=list)
    children = ChildCreateSerializer(many=True, required=False, default=list)
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
