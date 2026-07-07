"""
Expiry sweep: hard-deletes unverified registrations past their TTL, and only
ever deletes rows a registration itself created — never a pre-existing
matched family (the created_new_family branch).
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events.models import Event, EventTicket
from families.models import Child, Family, Parent

from .models import Registration
from .tasks import sweep_expired_registrations
from .tokens import generate_verification_token, hash_token


def _make_event():
    today = timezone.now().date()
    return Event.objects.create(name="Camp", start_date=today, end_date=today)


class ExpirySweepTests(TestCase):
    def setUp(self):
        self.event = _make_event()

    def _make_registration(
        self, *, expired, status=Registration.Status.PENDING_VERIFICATION
    ):
        family = Family.objects.create(last_name="Expiring")
        Parent.objects.create(
            first_name="Anna", relationship_type="Mother", family=family
        )
        child = Child.objects.create(first_name="Kim", family=family)
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=status,
        )
        EventTicket.objects.create(
            attendee=child, event=self.event, registration=registration
        )
        if expired:
            Registration.objects.filter(pk=registration.pk).update(
                expires_at=timezone.now() - timedelta(hours=1)
            )
        return registration, family

    def test_expired_unverified_registration_is_hard_deleted(self):
        registration, family = self._make_registration(expired=True)

        sweep_expired_registrations()

        self.assertFalse(Registration.objects.filter(pk=registration.pk).exists())
        self.assertFalse(Family.objects.filter(pk=family.pk).exists())

    def test_non_expired_registration_is_preserved(self):
        registration, family = self._make_registration(expired=False)

        sweep_expired_registrations()

        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertTrue(Family.objects.filter(pk=family.pk).exists())

    def test_confirmed_registration_past_original_ttl_is_untouched(self):
        registration, family = self._make_registration(
            expired=True, status=Registration.Status.CONFIRMED
        )

        sweep_expired_registrations()

        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertTrue(Family.objects.filter(pk=family.pk).exists())

    def test_pending_review_registration_past_original_ttl_is_untouched(self):
        registration, family = self._make_registration(
            expired=True, status=Registration.Status.PENDING_REVIEW
        )

        sweep_expired_registrations()

        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertTrue(Family.objects.filter(pk=family.pk).exists())

    def test_created_new_family_false_preserves_the_existing_family(self):
        """Not reachable via any code path in phase 1 (nothing sets
        created_new_family=False yet), but the sweep must already handle it
        correctly per the plan — this is the regression guard for whenever a
        future 'attach to a matched family' flow lands."""
        existing_family = Family.objects.create(last_name="PreExisting")
        pre_existing_child = Child.objects.create(
            first_name="Original", family=existing_family
        )
        new_child = Child.objects.create(
            first_name="NewlyAdded", family=existing_family
        )
        registration = Registration.objects.create(
            event=self.event,
            family=existing_family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            created_new_family=False,
        )
        ticket = EventTicket.objects.create(
            attendee=new_child, event=self.event, registration=registration
        )
        Registration.objects.filter(pk=registration.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        sweep_expired_registrations()

        self.assertFalse(Registration.objects.filter(pk=registration.pk).exists())
        self.assertFalse(EventTicket.objects.filter(pk=ticket.pk).exists())
        self.assertFalse(Child.objects.filter(pk=new_child.pk).exists())
        # The pre-existing family and its unrelated child must survive untouched.
        self.assertTrue(Family.objects.filter(pk=existing_family.pk).exists())
        self.assertTrue(Child.objects.filter(pk=pre_existing_child.pk).exists())
