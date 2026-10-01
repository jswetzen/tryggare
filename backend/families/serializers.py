from rest_framework import serializers

from registrations.models import Registration
from .models import Child, Family, Parent
from .services import create_family_with_members, update_family_with_members


class SafetyInfoDisclosureMixin:
    """Read-behind-reveal for the allergy/emergency-medical text.

    The staff API used to hand ``allergies``/``notes`` to anyone who could read
    a family at all, which under the seeded roles means every Volontär on every
    ``GET /api/families/`` — the whole event's special-category health data, on
    every poll of the check-in screen, with nothing in the audit log to say it
    happened. That is the same ambient exposure ``qr_info`` was split up to
    avoid (see ``families/qr_views.py`` and DPIA §2/§4); this mirrors the split
    on the authenticated check-in path.

    So the list/detail payload carries ``has_safety_info`` — a boolean saying
    *there is something here* — and the text itself only for a viewer who may
    already change it. Everyone else asks for it through
    ``FamilyViewSet.reveal_safety_info``, which writes one
    ``safety_info_revealed`` row per reveal. A glance at the roster stays
    distinguishable from an access to a child's allergy.

    Why "may change it" is the line, rather than a role name or a new
    permission: a viewer who can edit the field necessarily has to see it (an
    edit form that hides its own current value is not an edit form), and
    ``change_child``/``change_parent`` is exactly the grant that separates
    Koordinator/Administratör from Volontär in ``accounts/roles.py``. It is
    also the same string the write path checks, so moving the grant between
    roles needs no change here. ``Parent`` carries these fields too — an adult
    attendee's allergy is not less sensitive than a child's — so both
    serializers get this.
    """

    #: ``"app_label.codename"`` whose holder sees the text without revealing.
    health_text_permission: str

    def viewer_may_read_health_text(self) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return user.has_perm(self.health_text_permission)

    def get_has_safety_info(self, obj) -> bool:
        return bool(obj.allergies) or bool(obj.notes)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.viewer_may_read_health_text():
            # Masked to None rather than dropped: the check-in UI branches on
            # has_safety_info, and a missing key would read as "no consent
            # captured" instead of "not disclosed to you yet".
            data["allergies"] = None
            data["notes"] = None
        return data


class ParentSerializer(SafetyInfoDisclosureMixin, serializers.ModelSerializer):
    health_text_permission = "families.change_parent"

    name = serializers.ReadOnlyField()
    ticket_type = serializers.SerializerMethodField()
    ticket_details = serializers.SerializerMethodField()
    guardian_only_event_ids = serializers.SerializerMethodField()
    is_checked_in = serializers.SerializerMethodField()
    active_checkin_id = serializers.SerializerMethodField()
    checked_in_elsewhere = serializers.SerializerMethodField()
    has_safety_info = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "name",
            "phone",
            "email",
            "relationship_type",
            "allergies",
            "notes",
            "has_safety_info",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
            "guardian_only_event_ids",
            "is_checked_in",
            "active_checkin_id",
            "checked_in_elsewhere",
        ]
        read_only_fields = [
            "id",
            "name",
            "has_safety_info",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "ticket_type",
            "ticket_details",
            "guardian_only_event_ids",
            "is_checked_in",
            "active_checkin_id",
            "checked_in_elsewhere",
        ]

    def get_ticket_type(self, obj: Parent) -> str | None:
        t = obj.get_ticket_type()
        return t if t != "none" else None

    def get_ticket_details(self, obj: Parent) -> dict | None:
        if not obj.has_ticket:
            return None
        return obj.get_ticket_details()

    def get_guardian_only_event_ids(self, obj: Parent) -> list[str]:
        """Events on which this adult is a stored guardian-only adult of a
        CONFIRMED registration. The check-in screen needs it to agree with the
        server's ticket gate (checkins/eligibility.py): such an adult is exempt
        from the ``all`` ticket rule, and only on a confirmed registration.

        Deliberately separate from ``ticket_details``, which stays unscoped
        display data. Uses the ``guardian_registrations`` prefetch (confirmed
        registrations only) when the viewset provided it, a query otherwise.
        """
        if hasattr(obj, "guardian_registrations"):
            registrations = obj.guardian_registrations
        else:
            registrations = obj.guardian_only_registrations.filter(
                status=Registration.Status.CONFIRMED
            )
        return sorted({str(r.event_id) for r in registrations})

    # --- check-in state of an adult -------------------------------------
    #
    # An adult's check-in is PER SESSION (owner decision 2026-10-01): the
    # server's check-in only refuses a duplicate in the SAME session, so an
    # adult who is in session B is still admissible to C. A desk that is
    # looking at session C therefore passes ``?session=<id>`` and gets the
    # state of THAT session only, plus ``checked_in_elsewhere`` naming the
    # other sessions the adult is currently in. Without the parameter the old
    # answer stands (open record in ANY session) so no other caller changes.

    def _open_records(self, obj: Parent) -> list:
        """The adult's open (not checked out) records, session preloaded.

        Uses the viewset's ``active_checkins`` prefetch (which select_related's
        the session) when present; one query otherwise.
        """
        if hasattr(obj, "active_checkins"):
            return list(obj.active_checkins)
        from checkins.models import CheckInRecord

        return list(
            CheckInRecord.objects.filter(
                attendee=obj, check_out_time__isnull=True
            ).select_related("session")
        )

    def _records_here(self, obj: Parent) -> list:
        """Open records in the session the desk is looking at, or all of them
        when no session was asked for."""
        records = self._open_records(obj)
        session_id = self.context.get("session_id")
        if session_id is None:
            return records
        return [r for r in records if r.session_id == session_id]

    def get_is_checked_in(self, obj: Parent) -> bool:
        return len(self._records_here(obj)) > 0

    def get_active_checkin_id(self, obj: Parent) -> str | None:
        records = self._records_here(obj)
        return str(records[0].id) if records else None

    def get_checked_in_elsewhere(self, obj: Parent) -> list[str]:
        """Names of the OTHER sessions this adult is currently checked in to.

        Empty without a ``session`` parameter: with no session in view there is
        no "elsewhere".
        """
        session_id = self.context.get("session_id")
        if session_id is None:
            return []
        records = [r for r in self._open_records(obj) if r.session_id != session_id]
        records.sort(key=lambda r: r.check_in_time)
        names: list[str] = []
        for record in records:
            if record.session.name not in names:
                names.append(record.session.name)
        return names


class ChildSerializer(SafetyInfoDisclosureMixin, serializers.ModelSerializer):
    health_text_permission = "families.change_child"

    ticket_type = serializers.SerializerMethodField()
    ticket_details = serializers.SerializerMethodField()
    is_checked_in = serializers.SerializerMethodField()
    active_checkin_id = serializers.SerializerMethodField()
    has_safety_info = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "has_safety_info",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]
        read_only_fields = [
            "id",
            "has_safety_info",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]

    def get_ticket_type(self, obj: Child) -> str:
        """
        Get the type of ticket the child has.

        Returns:
            str: 'event', 'session', or 'none'
        """
        return obj.get_ticket_type()

    def get_ticket_details(self, obj: Child) -> dict:
        """
        Get detailed information about the child's tickets.

        Returns:
            dict: Ticket details including event_tickets and session_tickets lists
        """
        return obj.get_ticket_details()

    def get_is_checked_in(self, obj: Child) -> bool:
        """
        Check if the child has an active check-in (not checked out).

        Returns:
            bool: True if child has an active check-in, False otherwise
        """
        # Use prefetched active_checkins if available (Family viewset uses this)
        if hasattr(obj, "active_checkins"):
            return len(obj.active_checkins) > 0

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "checkin_records" in obj._prefetched_objects_cache
        ):
            checkin_records = obj.checkin_records.all()
            return any(record.check_out_time is None for record in checkin_records)

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord

        active_checkin = CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).first()
        return active_checkin is not None

    def get_active_checkin_id(self, obj: Child) -> str | None:
        """
        Get the ID of the active check-in record if any.

        Returns:
            str: The check-in record ID, or None if not checked in
        """
        # Use prefetched active_checkins if available (Family viewset uses this)
        if hasattr(obj, "active_checkins"):
            # An empty prefetched list means "not checked in", not "unknown":
            # falling through here re-queried once per checked-out child.
            return str(obj.active_checkins[0].id) if obj.active_checkins else None

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "checkin_records" in obj._prefetched_objects_cache
        ):
            checkin_records = obj.checkin_records.all()
            for record in checkin_records:
                if record.check_out_time is None:
                    return str(record.id)
            return None

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord

        active_checkin = CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).first()
        return str(active_checkin.id) if active_checkin else None


def _pending_payment_payload(family: Family) -> dict | None:
    """9.3 "unpaid at the door": the family's single pending_payment
    registration (if any), shaped for the check-in screen's unpaid banner.
    A family registers once per event and Registration.status blocks
    check-in the moment it isn't confirmed, so at most one row is relevant
    here — take the first. Uses the FamilyViewSet prefetch
    (`pending_payment_registrations`) when present; falls back to a direct
    query for serializer uses that don't go through that queryset (e.g. the
    walk-up FamilyCreateSerializer response, which never has one anyway).
    """
    if hasattr(family, "pending_payment_registrations"):
        registrations = family.pending_payment_registrations
    else:
        registrations = list(
            family.registrations.filter(
                status=Registration.Status.PENDING_PAYMENT
            ).select_related("payment")
        )

    registration = registrations[0] if registrations else None
    if registration is None:
        return None

    payment = getattr(registration, "payment", None)
    if payment is None:
        return None

    return {
        "registration_id": str(registration.id),
        "reference_code": registration.reference_code,
        "amount_owed": str(payment.balance),
        "currency": payment.currency,
    }


class FamilySerializer(serializers.ModelSerializer):
    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()
    pending_payment = serializers.SerializerMethodField()

    class Meta:
        model = Family
        fields = [
            "id",
            "last_name",
            "last_participation_date",
            "parents",
            "children",
            "display_name",
            "external_booking_id",
            "pending_payment",
        ]
        read_only_fields = [
            "id",
            "last_participation_date",
            "display_name",
            "external_booking_id",
            "pending_payment",
        ]

    def get_pending_payment(self, obj: Family) -> dict | None:
        return _pending_payment_payload(obj)


class FamilyDetailSerializer(serializers.ModelSerializer):
    """Extended serializer with full nested data for detail views"""

    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()
    pending_payment = serializers.SerializerMethodField()

    class Meta:
        model = Family
        fields = [
            "id",
            "last_name",
            "last_participation_date",
            "parents",
            "children",
            "display_name",
            "external_booking_id",
            "pending_payment",
        ]
        read_only_fields = [
            "id",
            "last_participation_date",
            "display_name",
            "external_booking_id",
            "pending_payment",
        ]

    def get_pending_payment(self, obj: Family) -> dict | None:
        return _pending_payment_payload(obj)


class ParentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating parents (without family field)"""

    health_consent_status = serializers.ChoiceField(
        choices=[
            Parent.HealthConsentStatus.NOT_APPLICABLE,
            Parent.HealthConsentStatus.GRANTED,
            Parent.HealthConsentStatus.DECLINED,
        ],
        default=Parent.HealthConsentStatus.NOT_APPLICABLE,
    )

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "relationship_type",
            "allergies",
            "notes",
            "health_consent_status",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """Same invariant as ChildCreateSerializer.validate() — see there."""
        status = attrs.get(
            "health_consent_status", Parent.HealthConsentStatus.NOT_APPLICABLE
        )
        if status != Parent.HealthConsentStatus.GRANTED:
            attrs["allergies"] = None
            attrs["notes"] = None
        return attrs


class ChildCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating children (without family field)"""

    health_consent_status = serializers.ChoiceField(
        choices=[
            Child.HealthConsentStatus.NOT_APPLICABLE,
            Child.HealthConsentStatus.GRANTED,
            Child.HealthConsentStatus.DECLINED,
        ],
        default=Child.HealthConsentStatus.NOT_APPLICABLE,
    )

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "health_consent_status",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """
        Health text is only ever stored once consent is granted — a
        declined/undecided status must not carry allergy/medical text even
        if the client sent some (enforced server-side, not just trusted from
        the UI).
        """
        status = attrs.get(
            "health_consent_status", Child.HealthConsentStatus.NOT_APPLICABLE
        )
        if status != Child.HealthConsentStatus.GRANTED:
            attrs["allergies"] = None
            attrs["notes"] = None
        return attrs


class FamilyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new family with nested parents and children"""

    parents = ParentCreateSerializer(many=True)
    children = ChildCreateSerializer(many=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "parents", "children", "display_name"]
        read_only_fields = ["id", "display_name"]

    def validate(self, data):
        """A family is a household of attendees — it can be all-parents,
        all-children, or mixed, but not empty."""
        if not data.get("parents") and not data.get("children"):
            raise serializers.ValidationError(
                "A family needs at least one parent or child"
            )
        return data

    def create(self, validated_data):
        """Create family with nested parents and children.

        Whoever is present at registration attests to the health-data consent
        decision — see create_family_with_members's docstring for why "first
        parent listed" is the right default here specifically (no separate
        attestor picker in the staff UI).
        """
        family, _created_parents, _created_children = create_family_with_members(
            last_name=validated_data.get("last_name", ""),
            parents_data=validated_data.pop("parents"),
            children_data=validated_data.pop("children"),
        )
        return family


class ParentUpsertSerializer(serializers.ModelSerializer):
    """Nested parent row inside FamilyUpdateSerializer — ``id`` present
    updates that existing Parent (ownership checked in
    ``update_family_with_members``), absent creates a new one attached to
    the family being edited. Otherwise identical to ParentCreateSerializer,
    including the same consent cross-field rule."""

    id = serializers.UUIDField(required=False)
    health_consent_status = serializers.ChoiceField(
        choices=[
            Parent.HealthConsentStatus.NOT_APPLICABLE,
            Parent.HealthConsentStatus.GRANTED,
            Parent.HealthConsentStatus.DECLINED,
        ],
        default=Parent.HealthConsentStatus.NOT_APPLICABLE,
    )

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "relationship_type",
            "allergies",
            "notes",
            "health_consent_status",
        ]

    def validate(self, attrs):
        """Same invariant as ParentCreateSerializer.validate() — see there."""
        status = attrs.get(
            "health_consent_status", Parent.HealthConsentStatus.NOT_APPLICABLE
        )
        if status != Parent.HealthConsentStatus.GRANTED:
            attrs["allergies"] = None
            attrs["notes"] = None
        return attrs


class ChildUpsertSerializer(serializers.ModelSerializer):
    """Nested child row inside FamilyUpdateSerializer — see
    ParentUpsertSerializer's docstring for the id-present-means-update
    convention."""

    id = serializers.UUIDField(required=False)
    health_consent_status = serializers.ChoiceField(
        choices=[
            Child.HealthConsentStatus.NOT_APPLICABLE,
            Child.HealthConsentStatus.GRANTED,
            Child.HealthConsentStatus.DECLINED,
        ],
        default=Child.HealthConsentStatus.NOT_APPLICABLE,
    )

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "health_consent_status",
        ]

    def validate(self, attrs):
        """Same invariant as ChildCreateSerializer.validate() — see there."""
        status = attrs.get(
            "health_consent_status", Child.HealthConsentStatus.NOT_APPLICABLE
        )
        if status != Child.HealthConsentStatus.GRANTED:
            attrs["allergies"] = None
            attrs["notes"] = None
        return attrs


class FamilyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for editing an existing family: change last_name and/or
    upsert nested parents/children in one atomic call. Never removes a
    member — see update_family_with_members's docstring."""

    parents = ParentUpsertSerializer(many=True, required=False)
    children = ChildUpsertSerializer(many=True, required=False)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "parents", "children", "display_name"]
        read_only_fields = ["id", "display_name"]

    def update(self, instance, validated_data):
        try:
            family, _updated_parents, _updated_children = update_family_with_members(
                family=instance,
                last_name=validated_data.get("last_name"),
                parents_data=validated_data.pop("parents", None),
                children_data=validated_data.pop("children", None),
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return family
