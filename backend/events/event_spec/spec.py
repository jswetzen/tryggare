"""Typed event spec (``event_spec_version: 1``).

Field set = the concrete model fields, minus an explicit exclusion list (see
``SpecParityTests``). Derived fields, counters, timestamps, live check-in state
and form-field config are not in it.
Rows refer to each other by ``key``, never by UUID. Descriptions are for the
LLM reading the JSON Schema, so they are plain English and not translated.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from django.utils import timezone
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

# Bounds on what one spec may carry, so a request cannot be made arbitrarily large.
# Copying an event goes through a spec, so these also cap what can be copied.
MAX_ROWS = 300
MAX_CHOICES = 100

KEY_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

Key = Annotated[
    str, StringConstraints(pattern=KEY_PATTERN, min_length=1, max_length=64)
]


def _localize(value: datetime) -> datetime:
    # A bare local time means the organiser's clock, as in the admin.
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_default_timezone())
    return value


LocalDateTime = Annotated[datetime, AfterValidator(_localize)]

PromoCodeText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_upper=True, min_length=1, max_length=50
    ),
]

Money = Annotated[Decimal, Field(max_digits=8, decimal_places=2)]

TicketRuleValue = Literal["open", "children", "all"]
AppliesToValue = Literal["parent", "child", "either"]

_TZ = "Without a UTC offset it is read as Europe/Stockholm local time."
_KEY = (
    "Identifier other rows use to refer to this one: lowercase letters, digits and "
    "single hyphens, unique among rows of the same kind. Export derives it from the "
    "name (so 'Child pass 0-12' becomes 'child-pass-0-12'); a rename therefore shows "
    "up as a removal plus an addition. Use the derived form."
)


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventSection(_Row):
    name: str = Field(max_length=255, description="Event name shown to guardians.")
    start_date: date = Field(
        description=(
            "First day of the event (ISO date). Ages are judged on this date, "
            "so ticket type birthdate bounds are derived from it."
        )
    )
    end_date: date = Field(description="Last day of the event (ISO date).")
    ticket_rule_default: TicketRuleValue = Field(
        default="open",
        description=(
            "Who needs a ticket to be checked in to a session that sets no rule of "
            "its own: 'open' (nobody), 'children' (children only), 'all' (everyone "
            "attending). Guardians who only drop children off never need one."
        ),
    )
    price: Money | None = Field(
        default=None,
        ge=0,
        description=(
            "Flat event price in SEK (Swedish kronor), used when the event has no "
            "ticket types. Null for a free event. Not needed when ticket types exist."
        ),
    )
    registration_opens_at: LocalDateTime | None = Field(
        default=None,
        description=(
            "Moment public self-serve registration opens (ISO 8601). " + _TZ + " "
            "Null together with registration_closes_at means self-serve "
            "registration is off. The window must not already be open when the spec "
            "is submitted: a person opens registration, not the spec."
        ),
    )
    registration_closes_at: LocalDateTime | None = Field(
        default=None,
        description=(
            "Moment public registration closes (ISO 8601). " + _TZ + " "
            "Null means no closing deadline. Must be after registration_opens_at."
        ),
    )
    header_image_url: str = Field(
        default="",
        max_length=200,
        description="Optional hosted URL of the hero image on the registration page. Empty for none.",
    )
    accent_color: str = Field(
        default="",
        max_length=7,
        description="Optional accent colour as #RRGGBB for the registration page. Empty for the default.",
    )


class SessionSpec(_Row):
    key: Key = Field(description=_KEY)
    name: str = Field(
        max_length=255, description="Session name, e.g. 'Saturday workshop'."
    )
    start_time: LocalDateTime = Field(
        description="When the session starts (ISO 8601). " + _TZ
    )
    end_time: LocalDateTime = Field(
        description="When the session ends (ISO 8601), after start_time. " + _TZ
    )
    ticket_rule: Literal["", "open", "children", "all"] = Field(
        default="",
        description=(
            "Who needs a ticket to be checked in here: 'open', 'children' or "
            "'all'. Empty string means follow event.ticket_rule_default."
        ),
    )
    adults_not_checked_in: bool = Field(
        default=False,
        description="True if only children are checked in here, not adults (a drop-off session).",
    )


class TicketTypeSpec(_Row):
    key: Key = Field(description=_KEY)
    name: str = Field(
        max_length=255,
        description="Ticket type name shown to guardians, e.g. 'Child 0-12'.",
    )
    price: Money = Field(
        ge=0,
        description="Price per ticket in SEK (Swedish kronor). 0 for a free ticket.",
    )
    applies_to: AppliesToValue = Field(
        default="either",
        description="Who may pick it on the public form: 'parent', 'child' or 'either'.",
    )
    min_birthdate: date | None = Field(
        default=None,
        description=(
            "Earliest allowed birth date (the attendee must be born on or after "
            "it), i.e. the oldest permitted. Must be exactly one day after an "
            "anniversary of event.start_date. Ages 'at most M' (e.g. a '0-12' "
            "label) on start 2027-06-18: start minus M+1 years plus one day, "
            "2014-06-19. Must not be later than max_birthdate. Null for no limit."
        ),
    )
    max_birthdate: date | None = Field(
        default=None,
        description=(
            "Latest allowed birth date (the attendee must be born on or before "
            "it), i.e. the youngest permitted. Must fall on the month and day of "
            "event.start_date. Ages 'at least N' on start 2027-06-18: start "
            "minus N years, e.g. 13 gives 2014-06-18. Null for no limit, which "
            "is right for a '0-12' label."
        ),
    )
    available_from: LocalDateTime | None = Field(
        default=None,
        description="Start of sale for this ticket type (ISO 8601). "
        + _TZ
        + " Null for no limit.",
    )
    available_until: LocalDateTime | None = Field(
        default=None,
        description="End of sale, e.g. an early-bird cutoff (ISO 8601). "
        + _TZ
        + " Null for no limit.",
    )
    is_hidden: bool = Field(
        default=False,
        description="True to hide it from the public form; only a promo code that unlocks it makes it selectable.",
    )
    kind: Literal["event", "session_bundle"] = Field(
        default="event",
        description="'event' covers the whole event; 'session_bundle' covers only the listed sessions.",
    )
    sessions: list[Key] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Keys of the sessions a 'session_bundle' ticket covers. Ignored for kind 'event'.",
    )
    capacity: int | None = Field(
        default=None,
        ge=0,
        description="Maximum number of tickets that can be sold. Null for unlimited.",
    )
    requires_ticket_type: Key | None = Field(
        default=None,
        description=(
            "Key of a ticket type that must be bought together with this one "
            "(at least one ticket of it in the same registration). Null for none."
        ),
    )
    max_per_required: int | None = Field(
        default=None,
        ge=0,
        description=(
            "How many of this ticket type are allowed per ticket of "
            "requires_ticket_type. Null for unlimited. Only read with requires_ticket_type."
        ),
    )
    sort_order: int = Field(
        default=0, ge=0, description="Display order on the form, lowest first."
    )
    is_active: bool = Field(
        default=True,
        description="False takes the ticket type out of use (hidden from the form).",
    )


class ExtraChoiceSpec(_Row):
    key: Key = Field(
        description=_KEY.replace("the name", "the label")
        + " Unique among the choices of one extra."
    )
    label: str = Field(max_length=255, description="Option label, e.g. 'M'.")
    price_delta: Money = Field(
        default=Decimal("0"),
        description="Amount in SEK added to the extra's price when this option is chosen. May be negative.",
    )
    sort_order: int = Field(default=0, ge=0, description="Display order, lowest first.")
    is_active: bool = Field(default=True, description="False retires the option.")


class ExtraSpec(_Row):
    key: Key = Field(description=_KEY)
    name: str = Field(
        max_length=255,
        description="Extra name, e.g. 'T-shirt'. Never free text from the guardian. An extra adds to the price; never use one as a discount or a flag.",
    )
    price: Money = Field(
        default=Decimal("0"),
        ge=0,
        description="Price in SEK (Swedish kronor). 0 for free.",
    )
    per_attendee: bool = Field(
        default=True,
        description="True when each attendee gets their own; false for one shared by the whole booking.",
    )
    applies_to: AppliesToValue = Field(
        default="either",
        description="Who is offered it: 'parent', 'child' or 'either'.",
    )
    requires_choice: bool = Field(
        default=False,
        description="True when the guardian must pick one of the choices (e.g. a size).",
    )
    required: bool = Field(
        default=False,
        description="True when the guardian must take it (rendered as must-choose, not an optional checkbox).",
    )
    default_selected: bool = Field(
        default=False, description="True for an opt-out extra that starts selected."
    )
    session: Key | None = Field(
        default=None,
        description="Key of the session this extra is tied to. Null means offered for the whole event.",
    )
    ticket_types: list[Key] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description=(
            "Keys of ticket types that gate this extra: it is offered only to an attendee "
            "holding any of them (for a per-booking extra, when anyone in the booking does). "
            "Empty means offered to everyone."
        ),
    )
    sort_order: int = Field(default=0, ge=0, description="Display order, lowest first.")
    is_active: bool = Field(
        default=True, description="False takes the extra out of use."
    )
    choices: list[ExtraChoiceSpec] = Field(
        default_factory=list,
        max_length=MAX_CHOICES,
        description="The options when requires_choice is true; ignored otherwise.",
    )


class PromoCodeSpec(_Row):
    key: Key = Field(description=_KEY.replace("the name", "the code"))
    code: PromoCodeText = Field(
        description="The code the guardian types. Trimmed and uppercased on input; matched case-insensitively and unique per event. 1-50 characters.",
    )
    discount_type: Literal["percent", "fixed"] = Field(
        default="fixed",
        description="'percent' (discount_value 0-100) or 'fixed' (SEK).",
    )
    discount_value: Money = Field(
        default=Decimal("0"),
        ge=0,
        description=(
            "Percent (0-100) or SEK amount depending on discount_type. 0 is valid "
            "for a pure unlock code."
        ),
    )
    applies_to_ticket_types: list[Key] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Keys of ticket types the discount applies to. Empty means the whole order.",
    )
    unlocks_ticket_types: list[Key] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Keys of hidden ticket types this code makes selectable.",
    )
    max_uses: int | None = Field(
        default=None,
        ge=0,
        description="How many times the code may be used. Null for unlimited.",
    )
    valid_from: LocalDateTime | None = Field(
        default=None,
        description="Code usable from this moment (ISO 8601). "
        + _TZ
        + " Null for no limit.",
    )
    valid_until: LocalDateTime | None = Field(
        default=None,
        description="Code usable until this moment (ISO 8601). "
        + _TZ
        + " Null for no limit.",
    )
    is_active: bool = Field(default=True, description="False disables the code.")


class EventSpec(_Row):
    event_spec_version: Literal[1] = Field(description="Spec format version. Always 1.")
    event: EventSection = Field(description="Event settings.")
    sessions: list[SessionSpec] = Field(
        default_factory=list, max_length=MAX_ROWS, description="Sessions of the event."
    )
    ticket_types: list[TicketTypeSpec] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Ticket types sold for the event.",
    )
    extras: list[ExtraSpec] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Paid or free add-ons, with their choices. An extra adds to the price; never a discount or a flag.",
    )
    promo_codes: list[PromoCodeSpec] = Field(
        default_factory=list,
        max_length=MAX_ROWS,
        description="Promo codes: the only way to express a discount, and/or unlocks for hidden ticket types. One code per registration.",
    )
