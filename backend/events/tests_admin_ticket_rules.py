"""Round 4, increment 3: the Event / Session admin forms explain the ticket
controls.

The admin evaluation said staff could not tell ``ticket_rule`` and
``adults_not_checked_in`` apart. These tests pin what fixed that: the help
text is on the rendered forms (EN and SV), the two controls share a fieldset,
the deprecated columns are not editable, and new sessions start with the
adults checkbox ticked WITHOUT that default leaking onto existing rows or
onto code that creates sessions through the ORM.
"""

import importlib
import re

from django.contrib.admin.sites import site
from django.db.migrations import AlterField
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone, translation

from accounts.models import AdminUser
from tests.support import NonManifestStaticfilesTestCase

from .admin import EventAdmin, SessionAdmin
from .models import (
    Event,
    RegistrationWindowStatus,
    Session,
    TicketRule,
    TicketType,
)


class AdminTicketRuleFormTests(NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("rulesadmin", "pw12345")
        today = timezone.now().date()
        cls.event = Event.objects.create(
            name="Rules Camp",
            start_date=today,
            end_date=today + timezone.timedelta(days=2),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _get(self, url, lang="en"):
        response = self.client.get(url, headers={"accept-language": lang})
        self.assertEqual(response.status_code, 200)
        return response

    # -- Session form -----------------------------------------------------

    def test_session_add_form_ticks_adults_not_checked_in(self):
        response = self._get(reverse("admin:events_session_add"))
        form = response.context["adminform"].form
        self.assertIs(form["adults_not_checked_in"].value(), True)
        self.assertRegex(
            response.content.decode(),
            r'<input[^>]*name="adults_not_checked_in"[^>]*checked',
        )

    def test_session_add_default_can_be_overridden_from_the_url(self):
        response = self._get(
            reverse("admin:events_session_add") + "?adults_not_checked_in="
        )
        self.assertFalse(
            response.context["adminform"].form["adults_not_checked_in"].value()
        )

    def test_session_change_form_shows_stored_value_not_the_add_default(self):
        session = Session.objects.create(
            event=self.event,
            name="Evening",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        response = self._get(reverse("admin:events_session_change", args=[session.pk]))
        self.assertIs(
            response.context["adminform"].form["adults_not_checked_in"].value(), False
        )

    def test_session_form_help_text_and_labels_en(self):
        html = self._get(reverse("admin:events_session_add")).content.decode()
        self.assertIn("Who needs a ticket to be checked in to this session.", html)
        # One line per option, named exactly as in the dropdown.
        for label in (
            "Open - no ticket required: anyone may be checked in",
            "Children need a ticket: a child without a ticket cannot be",
            "Everyone attending needs a ticket: children and adults alike",
        ):
            self.assertIn(label, html)
        self.assertIn('"Default Ticket Rule" field on the event', html)
        # F2: the pre-ticked default is announced next to the box.
        self.assertIn("The box is already ticked when you add a new session", html)
        # F3: adults unchecked => rule only matters for children.
        self.assertIn(
            "When adults are not checked in, the ticket rule only matters for children.",
            html,
        )
        # F4: what Active controls.
        self.assertIn("Shows this session in the session picker at the check-in", html)
        # The blank "inherit" choice is named, not "---------".
        self.assertIn("Same as the event&#x27;s default", html)

    def _make_session(self, event=None, **kwargs):
        return Session.objects.create(
            event=event or self.event,
            name="Evening",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            **kwargs,
        )

    def test_change_page_omits_the_pre_ticked_sentence_add_page_has_it(self):
        session = self._make_session()
        change = self._get(
            reverse("admin:events_session_change", args=[session.pk])
        ).content.decode()
        self.assertIn("When adults are not checked in", change)
        self.assertNotIn("already ticked when you add", change)
        add = self._get(reverse("admin:events_session_add")).content.decode()
        self.assertIn("already ticked when you add", add)
        # Same in Swedish.
        change_sv = self._get(
            reverse("admin:events_session_change", args=[session.pk]), lang="sv"
        ).content.decode()
        self.assertNotIn("redan ikryssad", change_sv)
        self.assertIn("När vuxna inte checkas in", change_sv)
        add_sv = self._get(
            reverse("admin:events_session_add"), lang="sv"
        ).content.decode()
        self.assertIn("redan ikryssad", add_sv)
        # The add-only sentence is not stored on the model help text.
        with translation.override("en"):
            self.assertNotIn(
                "already ticked",
                str(Session._meta.get_field("adults_not_checked_in").help_text),
            )

    def test_blank_ticket_rule_choice_names_the_events_default(self):
        children_event = Event.objects.create(
            name="Kids Camp",
            start_date=self.event.start_date,
            end_date=self.event.end_date,
            ticket_rule_default=TicketRule.CHILDREN,
        )
        session = self._make_session(event=children_event)
        en = self._get(
            reverse("admin:events_session_change", args=[session.pk])
        ).content.decode()
        self.assertIn("Same as the event&#x27;s default (Children need a ticket)", en)
        sv = self._get(
            reverse("admin:events_session_change", args=[session.pk]), lang="sv"
        ).content.decode()
        self.assertIn("Samma som evenemangets standard (Barn behöver biljett)", sv)
        # An event on the "open" default says so.
        open_session = self._make_session()
        en = self._get(
            reverse("admin:events_session_change", args=[open_session.pk])
        ).content.decode()
        self.assertIn(
            "Same as the event&#x27;s default (Open - no ticket required)", en
        )

    def test_add_form_keeps_the_generic_blank_choice(self):
        html = self._get(reverse("admin:events_session_add")).content.decode()
        self.assertRegex(
            html, r'<option value="" selected>Same as the event&#x27;s default</option>'
        )

    def test_is_active_help_is_two_sentences(self):
        with translation.override("en"):
            text = str(Session._meta.get_field("is_active").help_text)
        self.assertEqual(text.count(". ") + 1, 2, text)
        self.assertNotIn("online registration", text)

    def test_session_form_help_text_and_labels_sv(self):
        html = self._get(
            reverse("admin:events_session_add"), lang="sv"
        ).content.decode()
        self.assertIn(
            "Vem som behöver biljett för att checkas in på den här sessionen.", html
        )
        self.assertIn("Rutan är redan ikryssad när du lägger till en ny session", html)
        self.assertIn("Barn behöver biljett: ett barn utan biljett", html)
        self.assertIn("Standardregel för biljetter", html)
        self.assertIn("Gör att sessionen visas i sessionsväljaren", html)
        self.assertIn("Samma som evenemangets standard", html)

    def test_ticket_rule_and_adults_checkbox_share_a_fieldset(self):
        response = self._get(reverse("admin:events_session_add"))
        fieldsets = [list(fs.fields) for fs in response.context["adminform"]]
        shared = [f for f in fieldsets if "ticket_rule" in f]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0], ["ticket_rule", "adults_not_checked_in"])

    def test_session_form_does_not_expose_deprecated_columns(self):
        response = self._get(reverse("admin:events_session_add"))
        form_fields = response.context["adminform"].form.fields
        self.assertNotIn("requires_ticket", form_fields)
        self.assertNotIn("parent_checkin_policy", form_fields)

    def test_session_add_post_saves_ticked_and_unticked(self):
        base = {
            "event": str(self.event.pk),
            "start_time_0": "2030-01-01",
            "start_time_1": "10:00:00",
            "end_time_0": "2030-01-01",
            "end_time_1": "12:00:00",
            "ticket_rule": "",
        }
        url = reverse("admin:events_session_add")
        self.client.post(url, {**base, "name": "Ticked", "adults_not_checked_in": "on"})
        self.client.post(url, {**base, "name": "Unticked"})
        self.assertTrue(Session.objects.get(name="Ticked").adults_not_checked_in)
        self.assertFalse(Session.objects.get(name="Unticked").adults_not_checked_in)

    # -- Event form -------------------------------------------------------

    def test_event_form_help_text_en_and_sv(self):
        url = reverse("admin:events_event_add")
        en = self._get(url).content.decode()
        self.assertIn("The ticket rule that this event's sessions follow", en)
        self.assertIn("Check-in rules", en)
        self.assertIn("Everyone attending needs a ticket: children and adults", en)
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn("Den biljettregel som evenemangets sessioner följer", sv)
        self.assertIn("Regler för incheckning", sv)

    def test_event_form_does_not_expose_deprecated_policy(self):
        response = self._get(reverse("admin:events_event_add"))
        form_fields = response.context["adminform"].form.fields
        self.assertIn("ticket_rule_default", form_fields)
        self.assertNotIn("parent_checkin_policy_default", form_fields)

    def test_event_admin_inlines_are_all_read_only(self):
        # EventAdmin has no inlines today (sessions / ticket types are edited
        # on their own change pages). This guards against one being added
        # editable: any inline that does appear must lock every field.
        request = RequestFactory().get("/")
        request.user = self.user
        model_admin = EventAdmin(Event, site)
        for inline in model_admin.get_inline_instances(request, self.event):
            editable = set(inline.get_fields(request, None)) - set(
                inline.get_readonly_fields(request, None)
            )
            self.assertEqual(editable, set(), type(inline).__name__)

    # -- Ticket-type label rename ----------------------------------------

    def test_ticket_type_label_renamed(self):
        url = reverse("admin:events_tickettype_add")
        en = self._get(url).content.decode()
        self.assertIn("Can only be bought together with", en)
        self.assertNotIn("Requires Ticket Type", en)
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn("Får bara köpas tillsammans med", sv)
        self.assertNotIn("Kräver biljettyp", sv)
        with translation.override("en"):
            self.assertEqual(
                str(TicketType._meta.get_field("requires_ticket_type").verbose_name),
                "Can only be bought together with",
            )

    # -- Ticket type help -------------------------------------------------

    def test_ticket_type_applies_to_help_uses_dropdown_labels(self):
        url = reverse("admin:events_tickettype_add")
        en = self._get(url).content.decode()
        self.assertIn("Parent, Child or Either", en)
        for label in ("Parent", "Child", "Either"):
            self.assertIn(f">{label}</option>", en)
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn("Förälder, Barn eller Förälder eller barn", sv)
        for label in ("Förälder", "Barn", "Förälder eller barn"):
            self.assertIn(f">{label}</option>", sv)

    def test_birthdate_help_is_one_sentence_each(self):
        for name, word in (
            ("min_birthdate", "earliest"),
            ("max_birthdate", "latest"),
        ):
            with translation.override("en"):
                text = str(TicketType._meta.get_field(name).help_text)
            self.assertTrue(text.startswith(f"The {word} birth date allowed"), text)
            self.assertLess(len(text), 200)
            self.assertEqual(text.count(". "), 0)

    def test_ticket_type_max_per_label_matches_requires_label(self):
        url = reverse("admin:events_tickettype_add")
        en = self._get(url).content.decode()
        self.assertIn("Max per ticket of that type", en)
        self.assertNotIn("Max Per Required", en)
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn("Max per biljett av den typen", sv)
        self.assertNotIn("krävd", sv)

    # -- Event changelist -------------------------------------------------

    def test_event_list_shows_translated_registration_status(self):
        # setUpTestData's event has no window configured; add one per state.
        now = timezone.now()
        today = now.date()
        Event.objects.create(
            name="Open Camp",
            start_date=today,
            end_date=today,
            registration_opens_at=now - timezone.timedelta(days=1),
            registration_closes_at=now + timezone.timedelta(days=1),
        )
        Event.objects.create(
            name="Closed Camp",
            start_date=today,
            end_date=today,
            registration_opens_at=now - timezone.timedelta(days=3),
            registration_closes_at=now - timezone.timedelta(days=1),
        )
        Event.objects.create(
            name="Soon Camp",
            start_date=today,
            end_date=today,
            registration_opens_at=now + timezone.timedelta(days=3),
        )
        url = reverse("admin:events_event_changelist")
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn("Anmälningsperiodens status", sv)
        for text in ("Inte inställd", "Öppen", "Stängd", "Inte öppen än"):
            self.assertIn(f">{text}</td>", sv)
        self.assertNotIn(">not_configured</td>", sv)
        self.assertNotIn(">not_open_yet</td>", sv)
        en = self._get(url).content.decode()
        self.assertIn("Registration window status", en)
        for text in ("Not configured", "Open", "Closed", "Not open yet"):
            self.assertIn(f">{text}</td>", en)

    def test_event_list_registration_link_is_translated(self):
        url = reverse("admin:events_event_changelist")
        sv = self._get(url, lang="sv").content.decode()
        self.assertIn(">Visa sidan</a>", sv)
        en = self._get(url).content.decode()
        self.assertIn(">Open page</a>", en)

    def test_event_admin_lists_label_column_not_raw_property(self):
        self.assertIn("registration_window_status_label", EventAdmin.list_display)
        self.assertNotIn("registration_window_status", EventAdmin.list_display)
        admin_obj = EventAdmin(Event, site)
        self.assertEqual(
            admin_obj.registration_window_status_label(self.event),
            RegistrationWindowStatus.NOT_CONFIGURED.label,
        )

    # -- Session changelist -----------------------------------------------

    def test_session_list_column_order(self):
        # Name stays first (it is the change link); the raw override is last;
        # nothing was removed.
        self.assertEqual(
            list(SessionAdmin.list_display),
            [
                "name",
                "event",
                "is_active",
                "effective_ticket_rule",
                "adults_not_checked_in",
                "start_time",
                "end_time",
                "ticket_rule",
            ],
        )

    def test_session_changelist_renders_columns_in_that_order(self):
        Session.objects.create(
            event=self.event,
            name="Evening",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        response = self._get(reverse("admin:events_session_changelist"), lang="sv")
        html = response.content.decode()
        # Header cells carry a column-<field> class, in rendered order.
        columns = re.findall(r'<th scope="col"\s+class="[^"]*column-(\w+)', html)
        self.assertEqual(columns, list(SessionAdmin.list_display))
        # And the Swedish headers are the ones named in the review.
        for header in (
            "Biljettregel",
            "Gällande biljettregel",
            "Vuxna checkas inte in här",
        ):
            self.assertIn(header, html)


class SessionDefaultIsolationTests(TestCase):
    """The pre-ticked checkbox is an admin add-form default only."""

    def test_model_default_is_unchanged(self):
        field = Session._meta.get_field("adults_not_checked_in")
        self.assertIs(field.default, False)

    def test_orm_created_session_still_checks_adults_in(self):
        today = timezone.now().date()
        event = Event.objects.create(name="E", start_date=today, end_date=today)
        session = Session.objects.create(
            event=event,
            name="S",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertFalse(session.adults_not_checked_in)
        self.assertEqual(session.ticket_rule, "")
        self.assertEqual(session.effective_ticket_rule, TicketRule.OPEN)

    def test_admin_initial_does_not_touch_model(self):
        request = RequestFactory().get("/")
        initial = SessionAdmin(Session, site).get_changeform_initial_data(request)
        self.assertIs(initial["adults_not_checked_in"], True)

    def test_help_text_migration_rewrites_no_rows(self):
        """0023 only re-labels fields. It must contain no data operation and
        must not change any field default, or existing sessions could change
        meaning on deploy."""
        migration = importlib.import_module(
            "events.migrations.0023_ticket_rule_help_and_labels"
        ).Migration
        self.assertTrue(migration.operations)
        for operation in migration.operations:
            self.assertIsInstance(operation, AlterField)
        by_name = {(op.model_name, op.name): op.field for op in migration.operations}
        self.assertIs(by_name[("session", "adults_not_checked_in")].default, False)
        self.assertEqual(by_name[("session", "ticket_rule")].default, "")
