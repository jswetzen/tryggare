"""
Admin triage for outstanding balances (increment 0.3).

The failure this exists to prevent: a coordinator was asked "someone says
they paid but shows as unpaid" and completed the task *by guessing*. The
Payment changelist had no event filter, so the only outstanding balance it
could surface belonged to a different event entirely — and it marked that
one paid. An unreviewed database write, against the wrong family.

Two things had to be true for that to happen:

1. "Outstanding balances for Sommarläger 2026" was not expressible.
   ``list_filter`` carried no event, and ``search_fields`` covered only the
   reference code and the contact email.
2. Balance was a Python property, so it could not be sorted by — and cost
   one aggregate query per rendered row on the way.

These tests pin the filter, the search, the sort, and — most importantly —
that the SQL annotation and ``Payment.balance`` never disagree.
"""

from decimal import Decimal

from django.contrib.admin.views.main import ORDER_VAR
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from events.models import Event
from families.models import Family

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


def _make_payment(event, last_name, amount, *, status=Payment.Status.PENDING):
    family = Family.objects.create(last_name=last_name)
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email=f"{last_name.lower()}@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=Registration.Status.PENDING_PAYMENT,
        verified_at=timezone.now(),
    )
    return Payment.objects.create(
        registration=registration, amount=Decimal(amount), status=status
    )


class PaymentBalanceAnnotationTests(TestCase):
    """``Payment.balance`` (Python, per row) and
    ``Payment.balance_expression()`` (SQL, per page) are two implementations
    of one number. Anything that can make them disagree is a wrong figure on
    a screen someone is about to act on, so every ledger shape gets pinned
    against both.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("ledger", "pw12345")
        cls.event = _make_event("Sommarläger 2026")

    def _annotated(self, payment):
        return (
            Payment.objects.filter(pk=payment.pk)
            .annotate(**{Payment.BALANCE_ANNOTATION: Payment.balance_expression()})
            .get()
        )

    def _assert_agrees(self, payment, expected):
        annotated = self._annotated(payment)
        # Re-read the property from a fresh instance so a stale in-memory
        # `amount`/status can't accidentally make the two agree.
        fresh = Payment.objects.get(pk=payment.pk)
        self.assertEqual(fresh.balance, expected)
        self.assertEqual(getattr(annotated, Payment.BALANCE_ANNOTATION), expected)
        self.assertEqual(getattr(annotated, Payment.BALANCE_ANNOTATION), fresh.balance)

    def _record(self, payment, kind, amount):
        return record_payment_event(
            payment, kind=kind, amount=Decimal(amount), created_by=self.user
        )

    def test_no_ledger_events_leaves_the_full_amount_owed(self):
        """The LEFT JOIN matches nothing. Without Coalesce the SUMs are NULL
        and the whole expression collapses to NULL, not to `amount` — which
        would render an empty Balance column for exactly the rows a
        coordinator most needs to see."""
        payment = _make_payment(self.event, "Utan", "500.00")
        self.assertFalse(payment.events.exists())
        self._assert_agrees(payment, Decimal("500.00"))

    def test_partial_payment(self):
        payment = _make_payment(self.event, "Delvis", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "200.00")
        self._assert_agrees(payment, Decimal("300.00"))

    def test_exact_payment_lands_on_zero(self):
        payment = _make_payment(self.event, "Exakt", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "500.00")
        self._assert_agrees(payment, Decimal("0.00"))

    def test_overpayment_goes_negative(self):
        """A negative balance is a supported state, not a bug (case catalog
        §5.3: the family is owed money back). It must survive the SQL round
        trip with its sign intact."""
        payment = _make_payment(self.event, "Over", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "600.00")
        self._assert_agrees(payment, Decimal("-100.00"))

    def test_refund_reopens_the_balance(self):
        payment = _make_payment(self.event, "Retur", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "500.00")
        self._record(payment, PaymentEvent.Kind.REFUNDED, "200.00")
        self._assert_agrees(payment, Decimal("200.00"))

    def test_full_refund_restores_the_whole_amount(self):
        payment = _make_payment(self.event, "Helretur", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "500.00")
        self._record(payment, PaymentEvent.Kind.REFUNDED, "500.00")
        self._assert_agrees(payment, Decimal("500.00"))

    def test_adjustment_writes_the_balance_off(self):
        payment = _make_payment(self.event, "Justering", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "100.00")
        self._record(payment, PaymentEvent.Kind.ADJUSTMENT, "400.00")
        self._assert_agrees(payment, Decimal("0.00"))

    def test_all_three_kinds_at_once_over_several_rows(self):
        """Two received rows, a refund and an adjustment on one payment —
        the case where a per-kind SUM that quietly double-counted the join
        would show up."""
        payment = _make_payment(self.event, "Blandad", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "100.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "150.00")
        self._record(payment, PaymentEvent.Kind.REFUNDED, "50.00")
        self._record(payment, PaymentEvent.Kind.ADJUSTMENT, "25.00")
        # 500 - 250 + 50 - 25
        self._assert_agrees(payment, Decimal("275.00"))

    def test_a_free_registration_has_a_zero_balance(self):
        payment = _make_payment(self.event, "Gratis", "0.00")
        self._assert_agrees(payment, Decimal("0.00"))

    def test_one_payments_ledger_never_bleeds_into_another(self):
        """The aggregate runs over a join shared by the whole page. If the
        grouping were wrong, a big ledger on one row would inflate its
        neighbours — the quietest possible way to show a wrong number."""
        loaded = _make_payment(self.event, "Tung", "500.00")
        for _ in range(4):
            self._record(loaded, PaymentEvent.Kind.RECEIVED, "50.00")
        untouched = _make_payment(self.event, "Orord", "500.00")
        partial = _make_payment(self.event, "Halv", "800.00")
        self._record(partial, PaymentEvent.Kind.RECEIVED, "300.00")

        annotated = {
            p.pk: getattr(p, Payment.BALANCE_ANNOTATION)
            for p in Payment.objects.annotate(
                **{Payment.BALANCE_ANNOTATION: Payment.balance_expression()}
            )
        }
        for payment in (loaded, untouched, partial):
            with self.subTest(payment=str(payment)):
                self.assertEqual(
                    annotated[payment.pk], Payment.objects.get(pk=payment.pk).balance
                )
        self.assertEqual(annotated[loaded.pk], Decimal("300.00"))
        self.assertEqual(annotated[untouched.pk], Decimal("500.00"))
        self.assertEqual(annotated[partial.pk], Decimal("500.00"))

    def test_cancelled_payment_still_reports_its_balance(self):
        """`cancelled` is a status transition, not a ledger entry, so the
        arithmetic is untouched by it — both implementations must say so."""
        payment = _make_payment(self.event, "Avbruten", "500.00")
        self._record(payment, PaymentEvent.Kind.RECEIVED, "100.00")
        Payment.objects.filter(pk=payment.pk).update(status=Payment.Status.CANCELLED)
        self._assert_agrees(payment, Decimal("400.00"))

    # --- the N+1 the annotation exists to remove ------------------------

    def test_property_costs_a_query_per_payment_but_the_annotation_does_not(self):
        """The measurement behind the admin change: reading `.balance` off N
        payments is 1 + N queries (one aggregate each); the annotation is
        one query flat, whatever N is."""
        for i in range(10):
            payment = _make_payment(self.event, f"Rad{i}", "500.00")
            self._record(payment, PaymentEvent.Kind.RECEIVED, "100.00")

        with CaptureQueriesContext(connection) as per_row:
            [p.balance for p in Payment.objects.all()]
        self.assertEqual(len(per_row.captured_queries), 11)

        with CaptureQueriesContext(connection) as annotated:
            [
                getattr(p, Payment.BALANCE_ANNOTATION)
                for p in Payment.objects.annotate(
                    **{Payment.BALANCE_ANNOTATION: Payment.balance_expression()}
                )
            ]
        self.assertEqual(len(annotated.captured_queries), 1)


# The project ships WhiteNoise's manifest static storage, which refuses to
# resolve admin CSS unless collectstatic has run. Rendering an admin page in
# a test is unrelated to static-asset hashing, so swap in the plain backend.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class PaymentTriageAdminTest(TestCase):
    """Reconstructs the incident: two events, both carrying outstanding
    balances, and the question "who still owes money on Sommarläger 2026?"
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("triage-pay", "pw12345")
        cls.camp = _make_event("Sommarläger 2026")
        cls.other = _make_event("Höstretreat 2026", price=Decimal("300.00"))

        # Sommarläger: three families, three different amounts still owed.
        cls.lindqvist = _make_payment(cls.camp, "Lindqvist", "500.00")
        cls.bergman = _make_payment(cls.camp, "Bergman", "500.00")
        record_payment_event(
            cls.bergman,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("150.00"),
            created_by=cls.user,
        )
        cls.nyman = _make_payment(cls.camp, "Nyman", "500.00")
        record_payment_event(
            cls.nyman,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("500.00"),
            created_by=cls.user,
        )
        # The other event's outstanding balance — the row the coordinator
        # actually wrote to, having no way to tell it apart.
        cls.wrong_event = _make_payment(cls.other, "Sandberg", "300.00")

    def setUp(self):
        self.client.force_login(self.user)

    def _admin(self):
        # Looked up at call time: setUpTestData deep-copies class
        # attributes, and an AdminSite holds module references and so is not
        # deep-copyable.
        from django.contrib.admin.sites import site

        return site._registry[Payment]

    def _changelist(self, params=None):
        response = self.client.get(
            reverse("admin:registrations_payment_changelist"), params or {}
        )
        self.assertEqual(response.status_code, 200)
        return response

    # --- the missing filter ---------------------------------------------

    def test_event_is_a_sidebar_filter(self):
        self.assertIn(
            "registration__event", [f[0] for f in self._admin().list_filter if f]
        )

    def test_filtering_to_one_event_excludes_the_other_events_balances(self):
        response = self._changelist({"registration__event__id__exact": self.camp.id})
        rows = response.context["cl"].result_list
        self.assertEqual(
            {p.registration.event_id for p in rows},
            {self.camp.id},
            "the changelist still mixes events — this is the wrong-event write",
        )
        self.assertNotIn(self.wrong_event.pk, {p.pk for p in rows})

    def test_unfiltered_changelist_still_shows_both_events(self):
        """The guard only means something if the mixed view is the default —
        i.e. the coordinator really was looking at two events at once."""
        rows = self._changelist().context["cl"].result_list
        self.assertEqual(
            {p.registration.event_id for p in rows}, {self.camp.id, self.other.id}
        )

    # --- sorting by what is owed ----------------------------------------

    def test_outstanding_balances_for_one_event_sorted_biggest_first(self):
        """The whole point of the increment, in one request: narrow to one
        event, order by balance descending, read off who owes what."""
        model_admin = self._admin()
        # The ORDER_VAR index is into ChangeList.list_display, not
        # ModelAdmin.list_display: because this admin defines actions, the
        # changelist prepends an "action_checkbox" column, shifting every
        # index by one. Read it off the rendered changelist rather than
        # hardcoding the offset.
        index = self._changelist().context["cl"].list_display.index("balance_display")
        response = self._changelist(
            {
                "registration__event__id__exact": self.camp.id,
                ORDER_VAR: f"-{index}",
            }
        )
        rows = list(response.context["cl"].result_list)
        self.assertEqual(
            [
                (p.registration.family.last_name, model_admin.balance_display(p))
                for p in rows
            ],
            [
                ("Lindqvist", Decimal("500.00")),
                ("Bergman", Decimal("350.00")),
                ("Nyman", Decimal("0.00")),
            ],
        )

    def test_balance_column_is_declared_sortable(self):
        self.assertEqual(
            self._admin().balance_display.admin_order_field,
            Payment.BALANCE_ANNOTATION,
        )

    def test_balance_display_reads_the_annotation_not_the_property(self):
        """A zero balance is falsy; a truthiness-based fallback would send
        every settled row back through the per-row aggregate."""
        model_admin = self._admin()
        payment = model_admin.get_queryset(None).get(pk=self.nyman.pk)
        with CaptureQueriesContext(connection) as ctx:
            value = model_admin.balance_display(payment)
        self.assertEqual(value, Decimal("0.00"))
        self.assertEqual(len(ctx.captured_queries), 0)

    def test_balance_display_falls_back_to_the_property_when_unannotated(self):
        payment = Payment.objects.get(pk=self.bergman.pk)
        self.assertEqual(self._admin().balance_display(payment), Decimal("350.00"))

    # --- search ----------------------------------------------------------

    def test_search_by_family_last_name(self):
        rows = self._changelist({"q": "Lindqvist"}).context["cl"].result_list
        self.assertEqual([p.pk for p in rows], [self.lindqvist.pk])

    def test_search_by_reference_code_still_works(self):
        code = self.bergman.registration.reference_code
        rows = self._changelist({"q": code}).context["cl"].result_list
        self.assertEqual([p.pk for p in rows], [self.bergman.pk])

    def test_search_combines_with_the_event_filter(self):
        """Surname collisions across events are the realistic version of the
        incident — searching a name alone can still land on the wrong row."""
        twin = _make_payment(self.other, "Lindqvist", "300.00")
        rows = self._changelist({"q": "Lindqvist"}).context["cl"].result_list
        self.assertEqual({p.pk for p in rows}, {self.lindqvist.pk, twin.pk})
        rows = (
            self._changelist(
                {"q": "Lindqvist", "registration__event__id__exact": self.camp.id}
            )
            .context["cl"]
            .result_list
        )
        self.assertEqual([p.pk for p in rows], [self.lindqvist.pk])

    # --- columns ---------------------------------------------------------

    def test_changelist_renders_event_family_and_balance(self):
        body = self._changelist().content.decode()
        self.assertIn("Sommarläger 2026", body)
        self.assertIn("Lindqvist", body)
        self.assertIn("350", body)

    def test_family_column_is_blank_rather_than_querying_for_parents(self):
        payment = _make_payment(self.camp, "", "500.00")
        payment = self._admin().get_queryset(None).get(pk=payment.pk)
        with CaptureQueriesContext(connection) as ctx:
            self.assertIsNone(self._admin().family(payment))
        self.assertEqual(len(ctx.captured_queries), 0)

    # --- N+1 guard -------------------------------------------------------

    def test_changelist_query_count_does_not_scale_with_rows(self):
        """Balance was one aggregate per rendered row. Same page, 4 rows vs
        34: the query count must not move."""
        url = reverse("admin:registrations_payment_changelist")
        self.client.get(url)  # warm per-process caches

        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        baseline = len(small.captured_queries)

        for i in range(30):
            payment = _make_payment(self.camp, f"Extra{i}", "500.00")
            record_payment_event(
                payment,
                kind=PaymentEvent.Kind.RECEIVED,
                amount=Decimal("100.00"),
                created_by=self.user,
            )

        with CaptureQueriesContext(connection) as large:
            response = self.client.get(url)
        self.assertEqual(len(response.context["cl"].result_list), 34)
        self.assertEqual(
            len(large.captured_queries),
            baseline,
            f"changelist query count moved from {baseline} (4 rows) to "
            f"{len(large.captured_queries)} (34 rows) — an N+1 crept in",
        )

    def test_event_filter_options_do_not_scale_with_events(self):
        """RelatedOnlyFieldListFilter lists only events that have payments,
        and renders each via Event.__str__ (just the name, no join)."""
        url = reverse("admin:registrations_payment_changelist")
        self.client.get(url)

        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        baseline = len(small.captured_queries)

        for i in range(20):
            _make_event(f"Ovidkommande {i}")

        with CaptureQueriesContext(connection) as large:
            self.client.get(url)
        self.assertEqual(len(large.captured_queries), baseline)
