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


# ------------------------------------------------- owner decision d9245e21
# Option B: a guardian-only adult is responsible but NOT attending. The
# marker is a stored fact (Registration.guardian_only_parents), not
# inferred from "has no ticket".


def _marked(registration):
    return {p.first_name for p in registration.guardian_only_parents.all()}


def test_itemized_ticketless_adult_is_marked_and_ticketed_adult_is_not(
    api, itemized_event
):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[
                _parent("Anna"),
                _parent("Bo", ticket_type=str(itemized_event.adult_type.id)),
            ],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content
    assert _marked(Registration.objects.get()) == {"Anna"}


@pytest.fixture
def priced_flat_event(flat_event):
    flat_event.price = 500
    flat_event.save()
    return flat_event


def test_flat_event_guardian_only_adult_gets_no_ticket_and_is_not_charged(
    api, priced_flat_event
):
    response = _post(
        api,
        _payload(
            priced_flat_event,
            parents=[_parent(guardian_only=True)],
            children=[_child()],
        ),
    )
    assert response.status_code == 201, response.content

    registration = Registration.objects.get()
    guardian = Parent.objects.get()
    assert _marked(registration) == {"Anna"}
    assert not guardian.has_ticket
    # Only the child holds the flat ticket.
    assert EventTicket.objects.get().attendee_id == Child.objects.get().id
    # The flat price is per registration: the guardian changes nothing.
    assert calculate_total(registration) == 500


def test_flat_price_is_identical_with_and_without_a_guardian_only_adult(
    api, priced_flat_event
):
    with_guardian = _post(
        api,
        _payload(
            priced_flat_event,
            parents=[_parent(guardian_only=True)],
            children=[_child()],
            contact_email="a@example.com",
        ),
    )
    without = _post(
        api,
        _payload(
            priced_flat_event,
            parents=[_parent()],
            children=[_child()],
            contact_email="b@example.com",
        ),
    )
    assert with_guardian.status_code == without.status_code == 201
    totals = {calculate_total(r) for r in Registration.objects.all()}
    assert totals == {500}


def test_flat_event_ordinary_adult_still_gets_the_flat_ticket_and_no_marker(
    api, flat_event
):
    response = _post(
        api,
        _payload(flat_event, parents=[_parent()], children=[_child()]),
    )
    assert response.status_code == 201, response.content
    assert EventTicket.objects.count() == 2
    assert _marked(Registration.objects.get()) == set()


def test_flat_event_with_only_guardian_only_adults_is_rejected(api, flat_event):
    response = _post(
        api,
        _payload(flat_event, parents=[_parent(guardian_only=True)], children=[]),
    )
    assert response.status_code == 400
    assert not Registration.objects.exists()


def test_flat_event_extras_on_a_guardian_only_adult_are_refused(api, flat_event):
    extra = Extra.objects.create(
        event=flat_event,
        name="T-shirt",
        price=100,
        per_attendee=True,
        applies_to="parent",
    )
    response = _post(
        api,
        _payload(
            flat_event,
            parents=[_parent(guardian_only=True, extras=[{"extra": str(extra.id)}])],
            children=[_child()],
        ),
    )
    assert response.status_code == 400
    assert not Registration.objects.exists()


def test_child_only_ticket_types_adult_is_a_marked_guardian(api, itemized_event):
    """Every active type is child-only: the adult has nothing to pick, so
    ticket_type omitted/null (optionally with guardian_only: true) is the
    payload, and the adult is marked rather than rejected."""
    itemized_event.adult_type.delete()
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(guardian_only=True)],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content
    assert _marked(Registration.objects.get()) == {"Anna"}
    assert EventTicket.objects.get().attendee_id == Child.objects.get().id


def test_child_only_ticket_types_adult_without_the_flag_is_also_marked(
    api, itemized_event
):
    itemized_event.adult_type.delete()
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent()],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content
    assert _marked(Registration.objects.get()) == {"Anna"}


def test_child_only_ticket_types_adult_cannot_pick_a_child_ticket(api, itemized_event):
    itemized_event.adult_type.delete()
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(ticket_type=str(itemized_event.child_type.id))],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 400
    assert not Registration.objects.exists()


def test_guardian_only_flag_together_with_a_ticket_is_a_contradiction(
    api, itemized_event
):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[
                _parent(
                    guardian_only=True,
                    ticket_type=str(itemized_event.adult_type.id),
                )
            ],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 400
    assert response.json() == {
        "parents": [
            {
                "ticket_type": [
                    "A guardian who isn't attending can't also choose a ticket."
                ]
            }
        ]
    }


@pytest.mark.parametrize("status", ["granted", "declined"])
@pytest.mark.parametrize("flat", [True, False], ids=["flat", "itemized"])
def test_health_information_for_a_guardian_only_adult_is_rejected(
    api, flat_event, itemized_event, status, flat
):
    event = flat_event if flat else itemized_event
    parent = _parent(
        health_consent_status=status, allergies="Peanuts", guardian_only=flat
    )
    response = _post(
        api,
        _payload(event, parents=[parent], children=[_child(event)]),
    )
    assert response.status_code == 400
    assert response.json() == {
        "parents": [
            {
                "health_consent_status": [
                    "Health information can't be recorded for a guardian who isn't attending."
                ]
            }
        ]
    }
    assert not Registration.objects.exists()
    assert not Parent.objects.exists()


def test_guardian_only_adult_stores_no_per_attendee_data(api, itemized_event):
    # allergies sent with the default (not_applicable) consent status are
    # blanked by ParentCreateSerializer, exactly as for any adult.
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[_parent(allergies="Peanuts", notes="n")],
            children=[_child(itemized_event)],
        ),
    )
    assert response.status_code == 201, response.content
    guardian = Parent.objects.get()
    assert guardian.allergies is None and guardian.notes is None
    assert guardian.health_consent_status == "not_applicable"
    assert guardian.registration_extras.count() == 0
    assert not guardian.has_ticket


def test_ordinary_adult_may_still_record_health_information(api, itemized_event):
    response = _post(
        api,
        _payload(
            itemized_event,
            parents=[
                _parent(
                    ticket_type=str(itemized_event.adult_type.id),
                    health_consent_status="granted",
                    allergies="Shellfish",
                )
            ],
            children=[],
        ),
    )
    assert response.status_code == 201, response.content
    assert Parent.objects.get().allergies == "Shellfish"


# ------------------------------------------------------- migration backfill


def test_migration_backfill_marks_only_ticketless_adults_of_own_family_registrations(
    flat_event,
):
    import importlib

    from django.apps import apps

    from families.models import Family
    from registrations.tokens import generate_verification_token, hash_token

    migration = importlib.import_module(
        "registrations.migrations.0009_registration_guardian_only_parents"
    )

    def make(created_new_family):
        family = Family.objects.create(last_name="F")
        ticketed = Parent.objects.create(
            first_name="Ticketed", family=family, phone=PHONE
        )
        ticketless = Parent.objects.create(
            first_name="Ticketless", family=family, phone=PHONE
        )
        registration = Registration.objects.create(
            event=flat_event,
            family=family,
            contact_email="x@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            created_new_family=created_new_family,
        )
        EventTicket.objects.create(
            attendee=ticketed, event=flat_event, registration=registration
        )
        return registration, ticketless

    own, _ticketless = make(True)
    attached, _other = make(False)

    migration.backfill_guardian_only(apps, None)
    migration.backfill_guardian_only(apps, None)  # idempotent

    assert _marked(own) == {"Ticketless"}
    assert _marked(attached) == set()
