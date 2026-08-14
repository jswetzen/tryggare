import uuid

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ParentCheckinPolicy(models.TextChoices):
    """Who's allowed to check in as a parent/guardian, and whether they need a ticket.

    Lives at module level (not nested in Session) so both Event and Session
    can reference ParentCheckinPolicy.choices directly — a nested class
    would force one of the two field definitions into a lambda, which Django
    migrations can't serialize.
    """

    DISABLED = "disabled", _("Disabled")
    OPEN = "open", _("Open (no ticket required)")
    TICKET_REQUIRED = "ticket_required", _("Ticket required")


class AppliesTo(models.TextChoices):
    """Who a TicketType or Extra is offered to. Module level (like
    ParentCheckinPolicy above) so both models can reference the same
    choices without duplicating them."""

    PARENT = "parent", _("Parent")
    CHILD = "child", _("Child")
    EITHER = "either", _("Either")


class RegistrationWindowStatus(models.TextChoices):
    """Result of Event.registration_window_status — module level so the
    public registration API and the frontend gate can share the same
    vocabulary without importing the Event model itself."""

    NOT_CONFIGURED = "not_configured", _("Not configured")
    NOT_OPEN_YET = "not_open_yet", _("Not open yet")
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Event Name"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    parent_checkin_policy_default = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        default=ParentCheckinPolicy.OPEN,
        verbose_name=_("Default Parent Check-In Policy"),
        help_text=_(
            "Applied to sessions of this event that don't set their own policy."
        ),
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price"),
        help_text=_(
            "Leave blank for a free event. SEK only — Swish/Bankgiro are "
            "Sweden-only payment rails."
        ),
    )
    registration_opens_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Registration Opens At"),
        help_text=_(
            "Public self-serve registration only accepts submissions from "
            "this moment on. Leave this AND 'closes at' both blank to keep "
            "self-serve registration off for this event entirely — the "
            "correct default for events not meant for public sign-up (staff-"
            "only events, imports)."
        ),
    )
    registration_closes_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Registration Closes At"),
        help_text=_("Leave blank for no closing deadline."),
    )
    header_image_url = models.URLField(
        blank=True,
        verbose_name=_("Header Image URL"),
        help_text=_(
            "Optional hero image shown on the public registration page. "
            "Paste a hosted image URL — this system doesn't store "
            "uploaded images."
        ),
    )
    accent_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")],
        verbose_name=_("Accent Color"),
        help_text=_(
            "Optional hex accent color (e.g. #2563EB) for the public "
            "registration page hero. Leave blank for the default brand "
            "color."
        ),
    )

    class Meta:
        db_table = "events"
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        # D2: registration_window_status can't itself distinguish a
        # misconfigured window from "not open yet" — closes_at < opens_at
        # makes every moment either NOT_OPEN_YET or CLOSED, never OPEN, with
        # no error surfaced anywhere. Catch it at save time instead.
        if (
            self.registration_opens_at is not None
            and self.registration_closes_at is not None
            and self.registration_closes_at < self.registration_opens_at
        ):
            raise ValidationError(
                {
                    "registration_closes_at": _(
                        "Registration closes-at must be after opens-at."
                    )
                }
            )

    @property
    def is_paid(self) -> bool:
        return self.price is not None and self.price > 0

    @property
    def registration_window_status(self) -> str:
        """Single source of truth for whether the public registration form
        accepts submissions right now — read by both the public event-info
        endpoint (to decide what the landing page shows) and
        submit_registration (the actual enforcement point; the frontend gate
        is UX only, never trusted alone)."""
        if self.registration_opens_at is None and self.registration_closes_at is None:
            return RegistrationWindowStatus.NOT_CONFIGURED
        now = timezone.now()
        if self.registration_opens_at is not None and now < self.registration_opens_at:
            return RegistrationWindowStatus.NOT_OPEN_YET
        if (
            self.registration_closes_at is not None
            and now > self.registration_closes_at
        ):
            return RegistrationWindowStatus.CLOSED
        return RegistrationWindowStatus.OPEN


class Session(models.Model):
    ParentCheckinPolicy = ParentCheckinPolicy

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Session Name"))
    start_time = models.DateTimeField(verbose_name=_("Start Time"))
    end_time = models.DateTimeField(verbose_name=_("End Time"))
    is_active = models.BooleanField(default=False, verbose_name=_("Is Active"))
    requires_ticket = models.BooleanField(
        default=False, verbose_name=_("Requires Ticket")
    )
    parent_checkin_policy = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        blank=True,
        default="",
        verbose_name=_("Parent Check-In Policy"),
        help_text=_("Leave blank to inherit the event's default policy."),
    )
    event = models.ForeignKey(
        Event,
        related_name="sessions",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )

    class Meta:
        db_table = "sessions"
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")
        ordering = ["event__name", "start_time"]
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"

    @property
    def effective_parent_checkin_policy(self) -> str:
        return self.parent_checkin_policy or self.event.parent_checkin_policy_default


class TicketType(models.Model):
    """A priced, event-scoped category a guardian assigns to one attendee at
    self-serve registration (e.g. "Adult", "Youth 13-17", "Child 0-12").
    Distinct from the flat Event.price fallback used when an event has none
    configured — see registrations/pricing.py::calculate_total.

    Field caveats that belong here rather than in operator-facing help_text:

    ``capacity`` is a schema placeholder only — not yet enforced anywhere.
    A future capacity-accounting pass reads this field; until then it
    records intent, not a limit.

    ``is_active`` is a soft-retire flag rather than a delete, because
    ``EventTicket.ticket_type`` and ``SessionTicket.ticket_type`` both use
    ``on_delete=PROTECT``: once any ticket references a type, the row
    cannot be removed. Soft-retiring hides the type from the public form
    while preserving sold history (case catalog §9.4).

    ``sessions`` is read only when ``kind == Kind.SESSION_BUNDLE`` and
    ignored for ``Kind.EVENT``.

    ``max_per_required`` is read only alongside ``requires_ticket_type``;
    null means unlimited, but the dependency on at least one ticket of the
    required type still holds.
    """

    class Kind(models.TextChoices):
        EVENT = "event", _("Whole event")
        SESSION_BUNDLE = "session_bundle", _("Session bundle (e.g. one day)")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        related_name="ticket_types",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Price"))
    applies_to = models.CharField(
        max_length=10,
        choices=AppliesTo.choices,
        default=AppliesTo.EITHER,
        verbose_name=_("Applies To"),
    )
    min_birthdate = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Minimum Birthdate"),
        help_text=_(
            "The attendee must be born on or after this date. Leave blank "
            "for no lower age limit."
        ),
    )
    max_birthdate = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Maximum Birthdate"),
        help_text=_(
            "The attendee must be born on or before this date. Leave blank "
            "for no upper age limit."
        ),
    )
    available_from = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Available From")
    )
    available_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Available Until"),
        help_text=_(
            "E.g. an early-bird cutoff. Checked at submission time only — "
            "never recomputed for an existing registration."
        ),
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name=_("Hidden"),
        help_text=_(
            "Hidden from the public form; only selectable via a direct "
            "link/code (e.g. volunteer tickets)."
        ),
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.EVENT,
        verbose_name=_("Kind"),
    )
    sessions = models.ManyToManyField(
        Session,
        blank=True,
        related_name="bundle_ticket_types",
        verbose_name=_("Sessions"),
        help_text=_(
            "The sessions this ticket covers (e.g. a single day of a "
            "multi-day event). Only used when the kind above is a session "
            "bundle."
        ),
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Capacity"),
        help_text=_(
            "Leave blank for no limit. This number is not enforced yet — "
            "setting 50 will not stop a 51st booking."
        ),
    )
    requires_ticket_type = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dependent_ticket_types",
        verbose_name=_("Requires Ticket Type"),
        help_text=_(
            "If set, this ticket type may only be selected on a "
            "registration that also has at least one ticket of the "
            "required type (e.g. a free 'family member' type requiring a "
            "paid 'family ticket' type)."
        ),
    )
    max_per_required = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Max Per Required"),
        help_text=_(
            "How many tickets of this type each required ticket allows "
            "(e.g. 4 free family members per paid family ticket). Leave "
            "blank for no limit — one required ticket is still needed. "
            "Only used when 'Requires ticket type' is set."
        ),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort Order"))
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_(
            "Uncheck to take this ticket type out of use: it disappears "
            "from the registration form, and tickets already sold keep "
            "working."
        ),
    )

    class Meta:
        db_table = "ticket_types"
        verbose_name = _("Ticket Type")
        verbose_name_plural = _("Ticket Types")
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["event"])]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"

    def clean(self):
        super().clean()
        if self.requires_ticket_type_id is None:
            return
        if self.requires_ticket_type_id == self.id:
            raise ValidationError(
                {"requires_ticket_type": _("A ticket type cannot require itself.")}
            )
        if self.requires_ticket_type.event_id != self.event_id:
            raise ValidationError(
                {
                    "requires_ticket_type": _(
                        "The required ticket type must belong to the same event."
                    )
                }
            )


class PromoCode(models.Model):
    """A code a guardian enters at self-serve registration — either a
    discount, an unlock for an otherwise-`is_hidden` TicketType, or both.
    See registrations/pricing.py::calculate_discount for how the discount
    is computed, and registrations/views.py for where a code is resolved,
    locked, and its use counted.

    One code per Registration, ever (a single FK there, not M2M) — stacking
    is deliberately unrepresentable rather than validated away (case
    catalog §5.4).
    """

    class DiscountType(models.TextChoices):
        PERCENT = "percent", _("Percent")
        FIXED = "fixed", _("Fixed amount")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        related_name="promo_codes",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )
    code = models.CharField(
        max_length=50,
        verbose_name=_("Code"),
        help_text=_("Matched case-insensitively. Unique per event."),
    )
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.FIXED,
        verbose_name=_("Discount Type"),
    )
    discount_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name=_("Discount Value"),
        help_text=_(
            "0-100 for percent, kr for fixed. 0 is valid — a pure unlock "
            "code with no discount of its own (e.g. the ticket it unlocks "
            "is already 0 kr)."
        ),
    )
    applies_to_ticket_types = models.ManyToManyField(
        TicketType,
        blank=True,
        related_name="discount_promo_codes",
        verbose_name=_("Applies To Ticket Types"),
        help_text=_(
            "Leave empty to take the discount off the whole order. Pick "
            "ticket types to take it off only those lines."
        ),
    )
    unlocks_ticket_types = models.ManyToManyField(
        TicketType,
        blank=True,
        related_name="unlocking_promo_codes",
        verbose_name=_("Unlocks Ticket Types"),
        help_text=_(
            "Hidden ticket types that this code makes selectable — e.g. "
            "VIP2026 unlocking the VIP type for Weekend 2026."
        ),
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Max Uses"),
        help_text=_("Leave blank to let the code be used any number of times."),
    )
    uses_count = models.PositiveIntegerField(default=0, verbose_name=_("Uses Count"))
    valid_from = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Valid From")
    )
    valid_until = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Valid Until")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "promo_codes"
        verbose_name = _("Promo Code")
        verbose_name_plural = _("Promo Codes")
        constraints = [
            models.UniqueConstraint(
                fields=["event", "code"], name="unique_promo_code_per_event"
            )
        ]
        indexes = [models.Index(fields=["event"])]

    def save(self, *args, **kwargs):
        # Normalize to uppercase so the unique constraint actually enforces
        # case-insensitive uniqueness (Postgres text equality is
        # case-sensitive by default) and lookups can use a plain `code=`
        # exact match instead of a collation-dependent `iexact`.
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.event.name} - {self.code}"


class Extra(models.Model):
    """An optional paid or free add-on a guardian can attach to an attendee
    or to the registration as a whole (T-shirt, lunch, a shared cabin).

    Deliberately never a free-text field: dietary/health/accessibility
    disclosures live in dedicated, consent-gated fields elsewhere, not here —
    see the case catalog's "no free-text extras" decision.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event, related_name="extras", on_delete=models.CASCADE, verbose_name=_("Event")
    )
    session = models.ForeignKey(
        Session,
        null=True,
        blank=True,
        related_name="extras",
        on_delete=models.CASCADE,
        verbose_name=_("Session"),
        help_text=_(
            "Set for a session-scoped extra (e.g. one evening's dinner). "
            "Blank = event-wide."
        ),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    price = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name=_("Price")
    )
    per_attendee = models.BooleanField(
        default=True,
        verbose_name=_("Per Attendee"),
        help_text=_(
            "Unchecked for a per-registration extra shared by the whole "
            "booking (e.g. a cabin, a parking pass with quantity > 1)."
        ),
    )
    applies_to = models.CharField(
        max_length=10,
        choices=AppliesTo.choices,
        default=AppliesTo.EITHER,
        verbose_name=_("Applies To"),
    )
    requires_choice = models.BooleanField(
        default=False, verbose_name=_("Requires Choice")
    )
    required = models.BooleanField(
        default=False,
        verbose_name=_("Required"),
        help_text=_(
            "Must-choose-one, e.g. accommodation — renders as radio, not an "
            "optional checkbox."
        ),
    )
    default_selected = models.BooleanField(
        default=False,
        verbose_name=_("Default Selected"),
        help_text=_(
            "For an opt-out extra (e.g. food included by default, guardian "
            "can decline) — never model an opt-out as a negative price."
        ),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort Order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    cloned_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="clones",
        on_delete=models.SET_NULL,
        verbose_name=_("Cloned From"),
        help_text=_(
            "Informational only — the extra this was duplicated from, if "
            "any. No live link: editing either copy never affects the other."
        ),
    )

    class Meta:
        db_table = "extras"
        verbose_name = _("Extra")
        verbose_name_plural = _("Extras")
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["session"]),
        ]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"

    @property
    def origin(self) -> "Extra":
        """Walk cloned_from up to the root of this extra's clone chain."""
        node = self
        while node.cloned_from_id:
            node = node.cloned_from
        return node

    def lineage_siblings(self) -> list["Extra"]:
        """All other extras sharing this one's origin (the full clone tree,
        not just direct parent/children). Small trees expected (a handful
        of events), so a plain Python walk over `clones` is enough — no
        need for a recursive query.

        Example: A clones to B, B clones to C (A.cloned_from is None,
        B.cloned_from is A, C.cloned_from is B). Every node's origin is A,
        and each node's lineage_siblings() is the *other two* — not just
        its direct parent/child:

            A.lineage_siblings() == [B, C]
            B.lineage_siblings() == [A, C]
            C.lineage_siblings() == [A, B]
        """
        root = self.origin
        seen = {root.id}
        frontier = [root]
        result = [] if self.id == root.id else [root]
        while frontier:
            node = frontier.pop()
            for child in node.clones.select_related("event").all():
                if child.id in seen:
                    continue
                seen.add(child.id)
                frontier.append(child)
                if child.id != self.id:
                    result.append(child)
        return result


class ExtraChoice(models.Model):
    """One selectable option under an Extra with requires_choice=True (e.g.
    a T-shirt size). A real model rather than a JSON string list so
    per-choice pricing and referential integrity are both representable —
    editing a choice's label can never silently orphan an already-selected
    registration's choice the way a mutated JSON list could.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extra = models.ForeignKey(
        Extra,
        related_name="choice_rows",
        on_delete=models.CASCADE,
        verbose_name=_("Extra"),
    )
    label = models.CharField(max_length=255, verbose_name=_("Label"))
    price_delta = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name=_("Price Delta")
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort Order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = "extra_choices"
        verbose_name = _("Extra Choice")
        verbose_name_plural = _("Extra Choices")
        ordering = ["sort_order", "label"]
        indexes = [models.Index(fields=["extra"])]

    def __str__(self) -> str:
        return f"{self.extra.name} - {self.label}"


class Ticket(models.Model):
    """
    Base model for tickets. This is kept for backwards compatibility
    but new code should use EventTicket or SessionTicket.

    DEPRECATED: This model will be removed in a future version.
    Use EventTicket or SessionTicket instead.
    """

    EVENT_PASS = "EVENT_PASS"
    SESSION_TICKET = "SESSION_TICKET"
    NONE = "NONE"

    TICKET_TYPES = [
        (EVENT_PASS, _("Event Pass")),
        (SESSION_TICKET, _("Session Ticket")),
        (NONE, _("None")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=32, choices=TICKET_TYPES)
    attendee = models.ForeignKey(
        "families.Attendee", related_name="tickets", on_delete=models.CASCADE
    )
    session = models.ForeignKey(
        Session, related_name="tickets", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        db_table = "tickets"
        indexes = [
            models.Index(fields=["attendee"], name="tickets_attend_0ad1b0_idx"),
            models.Index(fields=["session"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} for {self.attendee}"


class EventTicket(models.Model):
    """
    Represents a ticket/pass for an entire event.
    Gives the attendee access to all sessions within the event.

    ``ticket_type`` is set only for itemized self-serve tickets (Phase 3+),
    and uses ``on_delete=PROTECT`` so a sold-against TicketType cannot be
    deleted out from under it (soft-retire via ``TicketType.is_active``
    instead). Null means a flat-price, staff-created, or imported ticket —
    unaffected by itemized pricing.

    ``price_at_registration`` is snapshotted once at submission and never
    recomputed, even if the ticket type's price changes afterwards. That is
    what makes mid-sale price edits safe by construction (case catalog
    §9.4) rather than something staff have to be careful about.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendee = models.ForeignKey(
        "families.Attendee",
        related_name="event_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Attendee"),
    )
    event = models.ForeignKey(
        Event,
        related_name="event_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )
    external_ticket_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("External Ticket Code"),
        help_text=_("ETicket code from the external registration system."),
    )
    registration = models.ForeignKey(
        "registrations.Registration",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="event_tickets",
        verbose_name=_("Registration"),
        help_text=_(
            "The registration this ticket came from, when a family signed "
            "up themselves online. Blank for tickets created by staff or "
            "brought in by an import."
        ),
    )
    ticket_type = models.ForeignKey(
        TicketType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="event_tickets",
        verbose_name=_("Ticket Type"),
        help_text=_(
            "The ticket type the family chose when registering. Blank for "
            "tickets created by staff or brought in by an import."
        ),
    )
    price_at_registration = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price At Registration"),
        help_text=_(
            "The price this ticket was sold at. Editing a price is safe — "
            "tickets already sold keep the price they were sold at."
        ),
    )

    class Meta:
        db_table = "event_tickets"
        verbose_name = _("Event Ticket")
        verbose_name_plural = _("Event Tickets")
        indexes = [
            models.Index(fields=["attendee"], name="event_ticke_attend_22981b_idx"),
            models.Index(fields=["event"]),
        ]
        unique_together = [["attendee", "event"]]

    def __str__(self) -> str:
        return f"Event Pass: {self.attendee} - {self.event}"


class SessionTicket(models.Model):
    """
    Represents a ticket for a specific session.
    Gives the attendee access only to the specified session.

    ``ticket_type`` and ``price_at_registration`` behave exactly as on
    EventTicket: the FK is set only for itemized self-serve tickets
    (Phase 3+) and is PROTECTed against deletion of the type, and the price
    is snapshotted once at submission and never recomputed, which is what
    makes mid-sale price edits safe (case catalog §9.4).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendee = models.ForeignKey(
        "families.Attendee",
        related_name="session_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Attendee"),
    )
    session = models.ForeignKey(
        Session,
        related_name="session_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Session"),
    )
    external_ticket_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("External Ticket Code"),
        help_text=_("ETicket code from the external registration system."),
    )
    registration = models.ForeignKey(
        "registrations.Registration",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="session_tickets",
        verbose_name=_("Registration"),
        help_text=_(
            "The registration this ticket came from, when a family signed "
            "up themselves online. Blank for tickets created by staff or "
            "brought in by an import."
        ),
    )
    ticket_type = models.ForeignKey(
        TicketType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="session_tickets",
        verbose_name=_("Ticket Type"),
        help_text=_(
            "The ticket type the family chose when registering. Blank for "
            "tickets created by staff or brought in by an import."
        ),
    )
    price_at_registration = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price At Registration"),
        help_text=_(
            "The price this ticket was sold at. Editing a price is safe — "
            "tickets already sold keep the price they were sold at."
        ),
    )

    class Meta:
        db_table = "session_tickets"
        verbose_name = _("Session Ticket")
        verbose_name_plural = _("Session Tickets")
        indexes = [
            models.Index(fields=["attendee"], name="session_tic_attend_c5a7b7_idx"),
            models.Index(fields=["session"]),
        ]
        unique_together = [["attendee", "session"]]

    def __str__(self) -> str:
        return f"Session Ticket: {self.attendee} - {self.session}"
