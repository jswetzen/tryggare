"""Setup shared by the event spec tests (a name test discovery does not match)."""

from datetime import UTC, date, datetime
from unittest.mock import patch

from families.models import Child, Family

from .models import Event, EventTicket, Session
from .event_spec._validate import validate

# The example's registration window is in 2027; pin "now" before it opens.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def at_now(now=NOW):
    return patch("events.models.timezone.now", return_value=now)


def validate_at_now(spec, event=None, now=NOW):
    with at_now(now):
        return validate(spec, event)


# Part B of docs/setup-checker-plan.md fixes the example; then this and its users go.
EXAMPLE_WARNINGS = {"bundle_replaces_pass"}


def without_example_warnings(warnings):
    return [w for w in warnings if w["code"] not in EXAMPLE_WARNINGS]


def by_path(issues):
    return {i["path"]: i for i in issues}


def empty_event(name="Empty", **fields):
    fields.setdefault("start_date", date(2027, 5, 1))
    fields.setdefault("end_date", date(2027, 5, 2))
    return Event.objects.create(name=name, **fields)


def make_child():
    return Child.objects.create(
        family=Family.objects.create(),
        first_name="T",
        last_name="C",
        birthdate=date(2020, 1, 1),
    )


def add_ticket(event, child=None):
    """Make ``event`` non-empty: one issued event ticket."""
    return EventTicket.objects.create(attendee=child or make_child(), event=event)


def foreign_session(name="Foreign"):
    """A session of another event, to refer to from this one's rows."""
    return Session.objects.create(
        event=empty_event("Other", start_date=date(2027, 1, 1)),
        name=name,
        start_time=datetime(2027, 1, 1, 9, tzinfo=UTC),
        end_time=datetime(2027, 1, 1, 10, tzinfo=UTC),
    )
