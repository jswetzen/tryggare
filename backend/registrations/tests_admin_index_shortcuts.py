"""Job-shaped entry point on the admin index: "Vem är skulden hos?".

A blind-test persona given the job "which families still owe money" spent
part of their 6 minutes translating that question into "which model do I
click" on an index that only lists model names. This is the fix: one link
on the index, phrased as the question, pointing straight at the existing
``HasOutstandingBalanceFilter`` (registrations/admin.py, ``?balance=owing``)
— see that filter's docstring for why "owing" is the one correct spelling
of the question, not a parallel definition invented here.

Gated on ``registrations.view_registration`` because that is the exact
permission ``RegistrationAdmin.has_view_permission`` checks — a staff user
who cannot open Registrations must not be shown a link into it.
"""

from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from events.models import Event
from families.models import Family

from tests.support import NonManifestStaticfilesTestCase

from .models import Payment, Registration
from .tokens import generate_verification_token, hash_token

LINK_HREF = "/admin/registrations/registration/?balance=owing"


def _make_owing_registration():
    today = timezone.now().date()
    event = Event.objects.create(
        name="Sommarläger 2027",
        start_date=today,
        end_date=today + timezone.timedelta(days=4),
        price=Decimal("500.00"),
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )
    family = Family.objects.create(last_name="Lindqvist")
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email="lindqvist@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=Registration.Status.PENDING_PAYMENT,
        verified_at=timezone.now(),
    )
    Payment.objects.create(registration=registration, amount=Decimal("500.00"))
    return registration


class AdminIndexBalanceShortcutTest(NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.registration = _make_owing_registration()

        cls.staff_with_perm = AdminUser.objects.create_user(
            "cansee", "pw12345", is_staff=True, is_active=True
        )
        cls.staff_with_perm.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="registrations",
                codename="view_registration",
            )
        )

        # Staff, but deliberately withheld the one permission the link is
        # gated on — the negative case the increment exists to cover.
        cls.staff_without_perm = AdminUser.objects.create_user(
            "cannotsee", "pw12345", is_staff=True, is_active=True
        )

        cls.superuser = AdminUser.objects.create_superuser("root", "pw12345")

    def test_link_present_for_user_with_permission(self):
        self.client.force_login(self.staff_with_perm)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(LINK_HREF, content)
        self.assertIn("Who owes money?", content)

    def test_link_absent_for_staff_without_permission(self):
        self.client.force_login(self.staff_without_perm)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(LINK_HREF, content)

    def test_link_present_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()
        self.assertIn(LINK_HREF, content)

    def test_model_list_is_still_present_alongside_the_shortcut(self):
        """Additive, not a replacement: the index still lists models."""
        self.client.force_login(self.staff_with_perm)
        response = self.client.get(reverse("admin:index"))
        app_list = response.context["app_list"]
        listed = {
            (app["app_label"], model["object_name"])
            for app in app_list
            for model in app["models"]
        }
        self.assertIn(("registrations", "Registration"), listed)

    def test_following_the_link_lands_on_a_filtered_changelist_with_results(self):
        """Not just a URL string match — the href actually has to resolve
        to a changelist filtered to families owing money, and the fixture
        family here must actually appear in it."""
        self.client.force_login(self.staff_with_perm)
        index_response = self.client.get(reverse("admin:index"))
        content = index_response.content.decode()
        self.assertIn(LINK_HREF, content)

        response = self.client.get(
            reverse("admin:registrations_registration_changelist"),
            {"balance": "owing"},
        )
        self.assertEqual(response.status_code, 200)
        results = list(response.context["cl"].result_list)
        self.assertIn(self.registration, results)
        self.assertGreaterEqual(len(results), 1)

    def test_staff_without_permission_cannot_follow_the_link_either(self):
        """Defense in depth: even if the link were somehow reached, the
        changelist itself must still refuse."""
        self.client.force_login(self.staff_without_perm)
        response = self.client.get(
            reverse("admin:registrations_registration_changelist"),
            {"balance": "owing"},
        )
        self.assertEqual(response.status_code, 403)
