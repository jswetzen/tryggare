import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ParentCheckinPolicy(models.TextChoices):
    """DEPRECATED (2026-10-01): superseded by ``TicketRule`` +
    ``Session.adults_not_checked_in``. Nothing reads it any more; it stays only
    so the migration that folds it into the new fields has a reverse, and goes
    away with the old columns in the admin increment.

    Who's allowed to check in as a parent/guardian, and whether they need a ticket.

    Lives at module level (not nested in Session) so both Event and Session
    can reference ParentCheckinPolicy.choices directly — a nested class
    would force one of the two field definitions into a lambda, which Django
    migrations can't serialize.
    """

    DISABLED = "disabled", _("Disabled")
    OPEN = "open", _("Open (no ticket required)")
    TICKET_REQUIRED = "ticket_required", _("Ticket required")


class TicketRule(models.TextChoices):
    """Who needs a ticket to be checked in to a session.

    Replaces two overlapping per-session controls that disagreed with each
    other (decided 2026-10-01): ``Session.requires_ticket`` (children only,
    enforced only in the check-in UI) and ``Session.parent_checkin_policy``
    (adults only, server-enforced). One rule, server-enforced, for everyone.
    Module level for the same reason as ``ParentCheckinPolicy``: Event and
    Session both reference ``TicketRule.choices``.

    Whether *adults are checked in at all* is a separate fact, not a rung on
    this ladder: ``Session.adults_not_checked_in``.
    """

    OPEN = "open", _("Open - no ticket required")
    CHILDREN = "children", _("Children need a ticket")
    ALL = "all", _("Everyone attending needs a ticket")


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
    ticket_rule_default = models.CharField(
        max_length=10,
        choices=TicketRule.choices,
        default=TicketRule.OPEN,
        verbose_name=_("Default Ticket Rule"),
        help_text=_(
            # One line per option (<br>: the admin renders help_text as
            # HTML) with a concrete case, because the option names alone did
            # not tell a coordinator what an adult at the door would meet.
            # The option names must match TicketRule's labels verbatim.
            "The ticket rule that this event's sessions follow, unless a "
            "session sets its own.<br>"
            "Open - no ticket required: anyone may be checked in, e.g. a "
            "drop-in play hour.<br>"
            "Children need a ticket: a child without a ticket cannot be "
            "checked in, adults need none, e.g. a children's workshop.<br>"
            "Everyone attending needs a ticket: children and adults alike, "
            "e.g. a ticketed evening show.<br>"
            "Guardians who only bring the children and do not attend "
            "themselves never need a ticket."
        ),
    )
    # DEPRECATED 2026-10-01: nothing reads this. Superseded by
    # ticket_rule_default (+ Session.adults_not_checked_in); kept only so the
    # data migration is cheaply reversible. Dropped in the admin increment.
    parent_checkin_policy_default = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        default=ParentCheckinPolicy.OPEN,
        verbose_name=_("Default Parent Check-In Policy"),
        help_text=_("Deprecated and no longer used - see 'Default Ticket Rule'."),
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
    TicketRule = TicketRule

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Session Name"))
    start_time = models.DateTimeField(verbose_name=_("Start Time"))
    end_time = models.DateTimeField(verbose_name=_("End Time"))
    # What this really controls (read from the code, 2026-10-01): the desk's
    # session picker (GET /sessions/active/, used by check-in and check-out);
    # for *supervised* check-ins, whether labels still print and whether a
    # child is still held in this session. Online registration never reads it.
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Is Active"),
        help_text=_(
            "Shows this session in the session picker at the check-in and "
            "check-out desks, and supervised check-ins only print labels "
            "while it is on. Tick it before the session starts; untick it "
            "when it is over."
        ),
    )
    ticket_rule = models.CharField(
        max_length=10,
        choices=TicketRule.choices,
        blank=True,
        default="",
        verbose_name=_("Ticket Rule"),
        help_text=_(
            # Option names mirror TicketRule's labels verbatim; the blank
            # choice is relabelled in SessionAdmin.formfield_for_choice_field.
            "Who needs a ticket to be checked in to this session. Leave it on "
            '"Same as the event\'s default" to follow the "Default Ticket '
            'Rule" field on the event.<br>'
            "Open - no ticket required: anyone may be checked in, e.g. a "
            "drop-in play hour.<br>"
            "Children need a ticket: a child without a ticket cannot be "
            "checked in, adults need none, e.g. a children's workshop.<br>"
            "Everyone attending needs a ticket: children and adults alike, "
            "e.g. a ticketed evening show.<br>"
            "Guardians who only bring the children and do not attend "
            "themselves never need a ticket."
        ),
    )
    adults_not_checked_in = models.BooleanField(
        default=False,
        verbose_name=_("Adults are not checked in here"),
        help_text=_(
            "Tick if only children are checked in to this session, not "
            "adults, as at a drop-off session. Leave it unticked if adults "
            "are checked in here too. When adults are not checked in, the "
            "ticket rule only matters for children."
        ),
        # The "already ticked when you add a new session" sentence is NOT
        # here: it is false on a change page, so SessionAdmin.get_form adds
        # it on the add form only.
    )
    # DEPRECATED 2026-10-01: neither of the next two fields is read by
    # anything. Superseded by ticket_rule / adults_not_checked_in; kept only so
    # the data migration is cheaply reversible. Dropped in the admin increment.
    requires_ticket = models.BooleanField(
        default=False,
        verbose_name=_("Requires Ticket"),
        help_text=_("Deprecated and no longer used - see 'Ticket Rule'."),
    )
    parent_checkin_policy = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        blank=True,
        default="",
        verbose_name=_("Parent Check-In Policy"),
        help_text=_(
            "Deprecated and no longer used - see 'Ticket Rule' and 'Adults "
            "are not checked in here'."
        ),
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
    def effective_ticket_rule(self) -> str:
        """The session's own rule, or the event's default when blank."""
        return self.ticket_rule or self.event.ticket_rule_default

    @property
    def children_need_ticket(self) -> bool:
        return self.effective_ticket_rule in (TicketRule.CHILDREN, TicketRule.ALL)

    @property
    def adults_need_ticket(self) -> bool:
        return self.effective_ticket_rule == TicketRule.ALL


class TicketType(models.Model):
    """A priced, event-scoped category a guardian assigns to one attendee at
    self-serve registration (e.g. "Adult", "Youth 13-17", "Child 0-12").
    Distinct from the flat Event.price fallback used when an event has none
    configured — see registrations/pricing.py::calculate_total.

    Field caveats that belong here rather than in operator-facing help_text:

    ``capacity`` is enforced for guest self-registration (registration
    dev-cycle round 4, increment 2, 2026-09-24; race/deadlock-safe as of
    the gate-review revision, 2026-09-25) — see
    registrations.services.ticket_type_sold_count for exactly what counts
    as "sold": every Registration status except cancelled, including a
    not-yet-verified ``pending_verification`` row for the full 48h
    verification TTL (a product decision confirmed on review, 2026-09-25 —
    an abandoned attempt holds its seat exactly like a real one until the
    expiry sweep removes it, since the two are indistinguishable before
    that). Staff are exempt: the EventTicket/SessionTicket admin add-form
    and the ticket-type-change wizard both let a type go over capacity,
    surfacing a passive warning rather than blocking the write — the same
    stance already taken on the age-window checks below.

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
        help_text=_(
            "Who may pick this ticket type on the public registration "
            "form: Parent, Child or Either. Staff can still assign it to "
            "anyone by hand in the admin, regardless of this setting."
        ),
    )
    min_birthdate = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Minimum Birthdate"),
        help_text=_(
            "The earliest birth date allowed (the attendee must be born on "
            "or after it), counted on the event's start date; leave blank "
            "for no limit."
        ),
    )
    max_birthdate = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Maximum Birthdate"),
        help_text=_(
            "The latest birth date allowed (the attendee must be born on or "
            "before it), counted on the event's start date; leave blank for "
            "no limit."
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
            "Leave blank for no limit. Enforced for guest self-registration: "
            "every registration counts against it except a cancelled one, "
            "including one still awaiting email verification (for up to 48 "
            "hours). Staff can still exceed it from this admin or the "
            "ticket-type-change wizard, with a warning to acknowledge first."
        ),
    )
    requires_ticket_type = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dependent_ticket_types",
        verbose_name=_("Can only be bought together with"),
        help_text=_(
            "If set, this ticket type can only be bought together with the "
            "ticket type chosen here: the registration must also include at "
            "least one ticket of that type (e.g. a free 'family member' type "
            "that can only be bought together with a paid 'family ticket' "
            "type)."
        ),
    )
    max_per_required = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Max per ticket of that type"),
        help_text=_(
            "How many tickets of this type are allowed per ticket of the "
            "type chosen in 'Can only be bought together with' (e.g. 4 free "
            "family members per paid family ticket). Leave blank for no "
            "limit; one ticket of that type is still needed."
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
        if self.requires_ticket_type_id is not None:
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
        self._clean_age_window()

    def _clean_age_window(self):
        """Enforce the single rule the owner settled on: age is judged once,
        on the event's start date, never recomputed. min_birthdate/
        max_birthdate are plain birthdate columns with no notion of "today"
        in their comparison (see registrations/services.py::AGE_MISMATCH_Q),
        so the only way a bound can silently encode a *different* rule —
        age at registration, age at some other milestone — is by not lining
        up with a whole-year anniversary of ``event.start_date``. This
        check closes that gap: a configured bound must sit on the exact
        date that relationship requires, not merely "near" the event.

        max_birthdate is the youngest-permitted cutoff, so it must fall on
        the start date's own month/day N years earlier (born that day =
        turns N on day one, exactly old enough). min_birthdate is the
        oldest-permitted cutoff, so it must fall one day *after* that
        anniversary (born the day before = already turned N+1 before the
        event started, too old by one day; born on or after this bound and
        they are still N or younger on day one).

        Skipped for an unsaved-event edge case (``event_id`` unset) and for
        whichever bound is left blank — blank means "no limit", not "not
        yet configured to match", see the field help text.
        """
        if self.event_id is None:
            return

        def example_years_before(anchor, years):
            """``anchor`` shifted back roughly ``years``, always a real date.

            Only interesting when ``anchor`` is 29 February: ``date.replace``
            raises ValueError for a non-leap target year, and this is running
            inside the branch that is *building a ValidationError message*, so
            the crash would escape ``full_clean`` (which only catches
            ValidationError) and turn a helpful 400 into a bare 500.

            Stepping further back to the nearest leap year rather than sliding
            to 28 February is deliberate: the example has to be a value that
            would actually pass this same check, and for a 29 February anchor
            only another 29 February does. The example is then a year or two
            older than the round number in the sentence, which is fine — it
            demonstrates the shape, and the exact date the operator needs is
            already spelled out alongside it.
            """
            for shift in range(years, years + 8):
                try:
                    return anchor.replace(year=anchor.year - shift)
                except ValueError:
                    continue
            raise AssertionError("no valid year within 8 of the requested shift")

        start = self.event.start_date
        day_after_start = start + timedelta(days=1)
        errors = {}
        if self.max_birthdate is not None and (
            self.max_birthdate.month,
            self.max_birthdate.day,
        ) != (start.month, start.day):
            errors["max_birthdate"] = _(
                "Age is judged on the event's start date (%(start)s), so "
                "this must fall exactly on an anniversary of it — e.g. "
                '%(example)s for a cutoff of "12 and under". A date that '
                "doesn't land on the anniversary would silently judge age "
                "on a different day than the event actually starts."
            ) % {
                "start": start.isoformat(),
                "example": example_years_before(start, 12).isoformat(),
            }
        if self.min_birthdate is not None and (
            self.min_birthdate.month,
            self.min_birthdate.day,
        ) != (day_after_start.month, day_after_start.day):
            errors["min_birthdate"] = _(
                "Age is judged on the event's start date, so this must "
                "fall exactly one day after an anniversary of it "
                "(%(day_after)s) — e.g. %(example)s to exclude anyone who "
                "has already turned 18 by the time the event starts."
            ) % {
                "day_after": day_after_start.isoformat(),
                "example": example_years_before(day_after_start, 18).isoformat(),
            }
        if errors:
            raise ValidationError(errors)


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
        # Explicit and title-cased: Django would otherwise derive
        # "ticket"/"tickets" from the class name, rendering lowercase next to
        # every sibling model's title-cased name. The model is deprecated and
        # hidden from the admin index, but autocomplete results and validation
        # errors still show this name.
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")
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
        # The door-only way to create one of these rows: the check-in desk's
        # one-tap grant (POST /api/event-tickets/grant/). A separate permission
        # rather than ``add_eventticket`` because that codename would also open
        # the Django-admin "add" form and POST /api/event-tickets/, which is
        # ticket *administration* and stays with Koordinator. Plain English name
        # for the same reason as the family DSAR permissions (``Permission.name``
        # is frozen into the database at migration time).
        permissions = [
            (
                "grant_eventticket_at_door",
                "Can grant an event ticket at the check-in desk",
            ),
        ]
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
        # Door-only grant, as for EventTicket: POST /api/session-tickets/grant/.
        # Deliberately not ``add_sessionticket`` (Django admin + the general
        # POST endpoint).
        permissions = [
            (
                "grant_sessionticket_at_door",
                "Can grant a session ticket at the check-in desk",
            ),
        ]
        indexes = [
            models.Index(fields=["attendee"], name="session_tic_attend_c5a7b7_idx"),
            models.Index(fields=["session"]),
        ]
        unique_together = [["attendee", "session"]]

    def __str__(self) -> str:
        return f"Session Ticket: {self.attendee} - {self.session}"
