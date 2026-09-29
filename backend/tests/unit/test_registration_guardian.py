"""
Guest-registration guardian rule (owner decision eb5d26f4).

1. A guardian is required only when the registration includes a child.
   Adults-only is fine; children-only is rejected.
2. Any adult on the registration is a guardian of ALL its children.
3. A guardian needn't hold a ticket ("guardian only": adult with no
   ticket_type on an itemized event).
4. Phone is required for every adult, ticketed or not.

These are pytest-style, so ``manage.py test`` does not discover them -- run
``uv run pytest tests/unit/test_registration_guardian.py``.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    SessionTicket,
    TicketType,
)
from families.models import Child, Parent
from registrations.models import Payment, Registration
from registrations.pricing import calculate_total
from registrations.services import sold_counts_for_event

URL = "/api/registrations/"
PHONE = "070-123 45 67"
NO_GUARDIAN = (
    "A registration with children needs at least one adult who is their guardian."
)
NO_PHONE = "A phone number is required for every adult."


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    # The anon submit throttle lives in the shared cache and would otherwise
    # make this file's request volume depend on run order.
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def flat_event(db):
    today = timezone.now().date()
    return Event.objects.create(
        name="Flat Camp",
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def itemized_event(flat_event):
    flat_event.name = "Itemized Camp"
    flat_event.save()
    flat_event.adult_type = TicketType.objects.create(
        event=flat_event, name="Adult", price=1100, applies_to=AppliesTo.PARENT
    )
    flat_event.child_type = TicketType.objects.create(
        event=flat_event,
        name="Child",
        price=400,
        applies_to=AppliesTo.CHILD,
        min_birthdate="2014-01-01",
        max_birthdate="2020-12-31",
    )
    return flat_event


def _parent(name="Anna", **overrides):
    parent = {"first_name": name, "phone": PHONE, "relationship_type": "Mother"}
    parent.update(overrides)
    return parent


def _child(event=None, **overrides):
    child = {"first_name": "Kim", "birthdate": "2018-01-01"}
    if event is not None and hasattr(event, "child_type"):
        child["ticket_type"] = str(event.child_type.id)
    child.update(overrides)
    return child


def _payload(event, *, parents, children, **overrides):
    payload = {
        "event": str(event.id),
        "contact_email": "guardian@example.com",
        "parents": parents,
        "children": children,
    }
    payload.update(overrides)
    return payload


def _post(api, payload, **extra):
    with patch("registrations.views.send_verification_email", return_value=True):
        return api.post(URL, payload, format="json", **extra)


# ---------------------------------------------------------------- rule 1


def test_children_only_is_rejected_with_a_parents_keyed_error(api, itemized_event):
    response = _post(
        api,
        _payload(itemized_event, parents=[], children=[_child(itemized_event)]),
    )
    assert response.status_code == 400
    assert response.json() == {"parents": [NO_GUARDIAN]}
    assert not Registration.objects.exists()
    assert not Child.objects.exists()


def test_children_only_with_parents_key_omitted_is_also_rejected(api, flat_event):
    payload = _payload(flat_event, parents=[], children=[_child()])
    del payload["parents"]
    response = _post(api, payload)
    assert response.status_code == 400
    assert response.json() == {"parents": [NO_GUARDIAN]}


def test_no_parent_and_no_child_keeps_the_original_error(api, flat_event):
    response = _post(api, _payload(flat_event, parents=[], children=[]))
    assert response.status_code == 400
    assert response.json() == {
        "non_field_errors": ["A registration needs at least one parent or child"]
    }


def test_children_only_error_is_swedish_under_accept_language_sv(api, flat_event):
    response = _post(
        api,
        _payload(flat_event, parents=[], children=[_child()]),
        HTTP_ACCEPT_LANGUAGE="sv",
    )
    assert response.status_code == 400
    assert response.json() == {
        "parents": [
            "En anmälan med barn behöver minst en vuxen som är barnens vårdnadshavare."
        ]
    }


def test_adults_only_is_still_accepted(api, itemized_event):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(ticket_type=str(itemized_event.adult_type.id))],
            children=[],
        ),
    )
    assert response.status_code == 201, response.content
    assert EventTicket.objects.count() == 1
    assert Child.objects.count() == 0


# ---------------------------------------------------------------- rule 3


def test_child_plus_ticketless_guardian_is_accepted_and_holds_no_ticket(
    api, itemized_event
):
    response = _post(
        api,
        _payload(
            itemized_event,
            # No ticket_type key at all: the "guardian only" representation.
            parents=[_parent()],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content

    guardian = Parent.objects.get()
    assert guardian.phone == PHONE
    assert not guardian.has_ticket
    assert guardian.event_tickets.count() == 0
    assert guardian.session_tickets.count() == 0

    child = Child.objects.get()
    assert child.family_id == guardian.family_id
    # Exactly one ticket line on the whole registration: the child's.
    ticket = EventTicket.objects.get()
    assert ticket.attendee_id == child.id
    assert not SessionTicket.objects.exists()

    # No seat consumed on the adult type, no price for the guardian.
    counts = sold_counts_for_event(itemized_event)
    assert counts.get(str(itemized_event.adult_type.id), 0) == 0
    assert counts.get(str(itemized_event.child_type.id), 0) == 1
    registration = Registration.objects.get()
    assert calculate_total(registration) == 400


def test_explicit_null_ticket_type_is_the_same_as_omitted(api, itemized_event):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(ticket_type=None)],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content
    assert not Parent.objects.get().has_ticket


def test_ticketless_guardian_consumes_no_capacity_on_a_full_adult_type(
    api, itemized_event
):
    itemized_event.adult_type.capacity = 1
    itemized_event.adult_type.save()
    first = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(ticket_type=str(itemized_event.adult_type.id))],
            children=[],
            contact_email="first@example.com",
        ),
    )
    assert first.status_code == 201, first.content

    # The adult type is now sold out; a guardian-only adult must not care.
    second = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent("Bo")],
            children=[_child(itemized_event)],
            contact_email="second@example.com",
        ),
    )
    assert second.status_code == 201, second.content


def test_guardian_only_registration_verifies_through_to_payment(api, itemized_event):
    with patch(
        "registrations.views.send_verification_email", return_value=True
    ) as mock_send:
        response = api.post(
            URL,
            _payload(
                itemized_event,
                parents=[_parent()],
                children=[_child(itemized_event)],
            ),
            format="json",
        )
    assert response.status_code == 201, response.content
    token = mock_send.call_args.args[1]

    with patch(
        "registrations.views.send_payment_instructions_email", return_value=True
    ):
        verify = api.get(f"/api/registrations/verify/{token}/")
    assert verify.status_code == 200, verify.content
    assert verify.json()["status"] == "pending_payment"
    assert Payment.objects.get().amount == 400


def test_a_registration_where_nobody_holds_a_ticket_is_rejected(api, itemized_event):
    response = _post(
        api,
        _payload(itemized_event, parents=[_parent()], children=[]),
    )
    assert response.status_code == 400
    assert not Registration.objects.exists()


def test_a_ticketless_child_is_still_rejected(api, itemized_event):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(ticket_type=str(itemized_event.adult_type.id))],
            children=[_child(ticket_type=None)],
        ),
    )
    assert response.status_code == 400
    assert not Registration.objects.exists()


def test_extras_on_a_ticketless_guardian_are_refused_not_dropped(api, itemized_event):
    extra = Extra.objects.create(
        event=itemized_event,
        name="T-shirt",
        price=100,
        per_attendee=True,
        applies_to="parent",
    )
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(extras=[{"extra": str(extra.id)}])],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 400
    assert response.json() == {
        "parents": {"0": ["Extras can only be added for an adult with a ticket."]}
    }
    assert not Registration.objects.exists()


def test_flat_price_event_still_ticks_every_attendee(api, flat_event):
    """No TicketTypes configured: there is no way to pick "no ticket", so the
    flat EventTicket is issued to every attendee exactly as before."""
    response = _post(
        api,
        _payload(flat_event, parents=[_parent()], children=[_child()]),
    )
    assert response.status_code == 201, response.content
    assert EventTicket.objects.count() == 2


# ---------------------------------------------------------------- rule 4


@pytest.mark.parametrize(
    "phone_override",
    [{"phone": ""}, {"phone": "   "}, {"phone": None}, "omit"],
    ids=["blank", "whitespace", "null", "omitted"],
)
def test_guardian_without_phone_is_rejected_with_a_row_keyed_error(
    api, itemized_event, phone_override
):
    parent = _parent()
    if phone_override == "omit":
        del parent["phone"]
    else:
        parent.update(phone_override)
    response = _post(
        api,
        _payload(itemized_event, parents=[parent], children=[_child(itemized_event)]),
    )
    assert response.status_code == 400
    assert response.json() == {"parents": [{"phone": [NO_PHONE]}]}
    assert not Registration.objects.exists()


def test_every_adult_needs_a_phone_and_the_error_names_the_right_row(
    api, itemized_event
):
    ticket = str(itemized_event.adult_type.id)
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[
                _parent(ticket_type=ticket),
                _parent("Bo", phone="", ticket_type=ticket),
            ],
            children=[],
        ),
    )
    assert response.status_code == 400
    assert response.json() == {"parents": [{}, {"phone": [NO_PHONE]}]}


def test_ticketed_adult_without_phone_is_rejected_too(api, itemized_event):
    """The phone rule is about being an adult on the registration, not about
    being ticketless."""
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(phone="", ticket_type=str(itemized_event.adult_type.id))],
            children=[],
        ),
    )
    assert response.status_code == 400
    assert response.json() == {"parents": [{"phone": [NO_PHONE]}]}


def test_phone_error_is_swedish_under_accept_language_sv(api, itemized_event):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(phone="")],
            children=[_child(itemized_event)],
        ),
        HTTP_ACCEPT_LANGUAGE="sv",
    )
    assert response.status_code == 400
    assert response.json() == {
        "parents": [
            {
                "phone": [
                    "Ange ett telefonnummer så att vi kan nå dig under evenemanget."
                ]
            }
        ]
    }
