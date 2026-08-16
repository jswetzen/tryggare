"""
R1 (revision round 1): the balance annotation was wrong whenever a search
term was present.

Mechanism, DB-verified before the fix (reproduced independently by the
design critic against the live persona fixture, and again here from
scratch): ``search_fields`` reaching ``family__attendees__{first,last}_name``
is a join onto a multi-valued relation. Combined with the ``Sum()`` in
``Payment.balance_expression`` (also joined onto the same top-level
queryset), the fan-out from N attendees multiplied every PaymentEvent row by
N. A family with 4 attendees, one registration, amount 3300.00 and one
RECEIVED event of 1000.00 truly owes 2300.00 — and rendered -700.00 under
search. ``distinct()`` cannot fix this: the GROUP BY collapses on the
registration's own columns, which are identical across the fanned-out rows.

The fix (``Payment.balance_subquery`` / ``Payment.family_balance_subquery``,
registrations/models.py) computes the balance as a correlated subquery
instead of a join, so no join the outer queryset adds — search or otherwise
— can touch it. These tests are the regression guard: every one of them
applies a search term, because that is exactly the condition none of the
increment's original tests exercised.
"""

from decimal import Decimal

from django.contrib.admin.sites import site
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from events.models import Event
from families.models import Child, Family, Parent

from .models import Payment, PaymentEvent, Registration
from .services import record_payment_event
from .tokens import generate_verification_token, hash_token


def _make_event(name, price=Decimal("500.00")):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today + timezone.timedelta(days=4),
        price=price,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_family_with_attendees(last_name, *, parents=2, children=2):
    """A family with more than one attendee — the shape R1 needs to
    reproduce. Each attendee row is exactly what fans a naive join out."""
    family = Family.objects.create(last_name=last_name)
    for i in range(parents):
        Parent.objects.create(
            family=family,
            first_name=f"Parent{i}",
            last_name=last_name,
            relationship_type="MOM" if i == 0 else "DAD",
            email=f"{last_name.lower()}{i}@example.com",
        )
    for i in range(children):
        Child.objects.create(
            family=family,
            first_name=f"Child{i}",
            last_name=last_name,
            birthdate=timezone.now().date().replace(year=2018),
        )
    return family


def _make_registration(event, family, amount, *, received=None):
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email=f"{family.last_name.lower()}@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=Registration.Status.PENDING_PAYMENT,
        verified_at=timezone.now(),
    )
    payment = Payment.objects.create(registration=registration, amount=Decimal(amount))
    if received is not None:
        record_payment_event(
            payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal(received),
            created_by=AdminUser.objects.first(),
        )
        payment.refresh_from_db()
    return registration, payment


class RegistrationSearchBalanceTests(TestCase):
    """The registration changelist's balance column must not move when a
    search term is applied."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("finance", "pw12345")
        cls.event = _make_event("Sommarläger 2027")
        # 4 attendees (2 parents, 2 children) — matches the DB-verified
        # repro exactly: VD7SLEUF, Ahlberg, 4 attendees.
        cls.family = _make_family_with_attendees("Ahlberg", parents=2, children=2)
        cls.registration, cls.payment = _make_registration(
            cls.event, cls.family, "3300.00", received="1000.00"
        )
        # A second, single-attendee family that must NOT be dragged into
        # results by the search term below.
        cls.other_family = _make_family_with_attendees("Okvist", parents=1, children=0)
        cls.other_registration, cls.other_payment = _make_registration(
            _make_event("Vinterläger 2027"), cls.other_family, "1400.00"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _admin(self):
        # Looked up at call time, same reasoning as PaymentBalanceAnnotationTests:
        # setUpTestData deep-copies class attributes and an AdminSite is not
        # deep-copyable.
        return site._registry[Registration]

    def _changelist(self, params=None):
        response = self.client.get(
            reverse("admin:registrations_registration_changelist"), params or {}
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_balance_is_correct_without_a_search_term(self):
        rows = self._changelist().context["cl"].result_list
        row = next(r for r in rows if r.pk == self.registration.pk)
        annotated = getattr(row, Payment.BALANCE_ANNOTATION)
        self.assertEqual(annotated, Decimal("2300.00"))

    def test_balance_is_still_correct_under_a_surname_search(self):
        """The point of this test. Before the fix this rendered -700.00:
        amount(3300) - received(1000) * attendees(4) = 3300 - 4000 = -700."""
        response = self._changelist({"q": "Ahlberg"})
        rows = response.context["cl"].result_list
        self.assertEqual([r.pk for r in rows], [self.registration.pk])
        annotated = getattr(rows[0], Payment.BALANCE_ANNOTATION)
        self.assertEqual(annotated, Decimal("2300.00"))
        # Must also agree with the ledger's own source of truth.
        self.assertEqual(annotated, self.payment.balance)

    def test_balance_under_search_matches_a_child_first_name_search_too(self):
        """The fan-out join reaches first_name and last_name independently
        — pin both, since a fix that only handles last_name would still be
        wrong for the far more common case of a caller giving a child's
        first name."""
        response = self._changelist({"q": "Child0"})
        rows = response.context["cl"].result_list
        self.assertEqual([r.pk for r in rows], [self.registration.pk])
        self.assertEqual(
            getattr(rows[0], Payment.BALANCE_ANNOTATION), Decimal("2300.00")
        )

    def test_owing_filter_agrees_with_the_column_under_search(self):
        """Before the fix, a searched-and-filtered view filed this family
        (owing 2300 kr) under "Reglerad" — the annotation the filter reads
        was the same wrong -700.00."""
        response = self._changelist({"q": "Ahlberg", "balance": "owing"})
        rows = response.context["cl"].result_list
        self.assertEqual([r.pk for r in rows], [self.registration.pk])

        response = self._changelist({"q": "Ahlberg", "balance": "settled"})
        rows = response.context["cl"].result_list
        self.assertEqual(
            [r.pk for r in rows],
            [],
            "a family owing 2300 kr must not appear under Settled, search term or not",
        )

    def test_search_still_excludes_unrelated_families(self):
        response = self._changelist({"q": "Ahlberg"})
        rows = response.context["cl"].result_list
        self.assertNotIn(self.other_registration.pk, {r.pk for r in rows})

    def test_changelist_query_count_does_not_scale_with_search_or_attendees(self):
        """The subquery fix must still be O(1) queries for the page, search
        term or not — a per-row fallback would silently reintroduce the N+1
        the original annotation existed to kill."""
        url = reverse("admin:registrations_registration_changelist")
        self.client.get(url, {"q": "Ahlberg"})  # warm caches
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url, {"q": "Ahlberg"})
        self.assertLess(len(ctx.captured_queries), 15)


class FamilyBalanceSubqueryTests(TestCase):
    """R6: the family changelist's own balance column, added with the same
    Subquery mechanism as R1 — and exposed to the exact same fan-out risk,
    one relation further up (Family -> registrations is already one-to-many,
    stacked under FamilyAdmin's own attendees__* search join)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("finance2", "pw12345")
        cls.family = _make_family_with_attendees("Bergqvist", parents=2, children=2)
        cls.reg1, cls.pay1 = _make_registration(
            _make_event("Sommarläger 2027"),
            cls.family,
            "3300.00",
            received="1000.00",
        )
        cls.reg2, cls.pay2 = _make_registration(
            _make_event("Familjehelg 2027"), cls.family, "1950.00", received="400.00"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _changelist(self, params=None):
        response = self.client.get(
            reverse("admin:families_family_changelist"), params or {}
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_family_balance_sums_across_registrations_without_search(self):
        rows = self._changelist().context["cl"].result_list
        row = next(r for r in rows if r.pk == self.family.pk)
        self.assertEqual(getattr(row, Payment.BALANCE_ANNOTATION), Decimal("3850.00"))

    def test_family_balance_sums_across_registrations_under_search(self):
        """Same fan-out shape as R1, one relation up: registrations
        (one-to-many from family) summed under the same query as the
        attendees (one-to-many from family) search join. A naive join-based
        Sum here would multiply the per-registration ledger totals by the
        attendee count all over again."""
        response = self._changelist({"q": "Child0"})
        rows = response.context["cl"].result_list
        self.assertEqual([r.pk for r in rows], [self.family.pk])
        self.assertEqual(
            getattr(rows[0], Payment.BALANCE_ANNOTATION), Decimal("3850.00")
        )
        self.assertEqual(
            getattr(rows[0], Payment.BALANCE_ANNOTATION),
            self.pay1.balance + self.pay2.balance,
        )
