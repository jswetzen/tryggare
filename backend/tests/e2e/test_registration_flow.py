"""
Self-Serve Registration E2E Tests

Covers the public /register/[eventId] submission form and the
/register/verify/[token] landing page, and confirms the check-in eligibility
gate: a self-serve-registered child must not be checkable in until their
registration is confirmed, and must become checkable in immediately once it
is.

The verification-email step is intentionally not driven through a real
inbox/log-file read here (that path is exercised manually — see the Track 1
plan's Verification section, "pull the verification link from web.log").
Instead the "confirmed" scenario seeds a Registration via the ORM with a
known plaintext token (mirroring exactly what the verification email would
have contained) and drives the real /register/verify/[token] page through
the browser — this still exercises the full verify view + frontend + the
check-in gate end-to-end, without depending on log-file paths that vary by
deployment.

Run with:
    pytest backend/tests/e2e/test_registration_flow.py -v
"""

import pytest
from selenium.webdriver.common.by import By

from tests.e2e.base import E2ETestBase, TestDataMixin
from events.models import EventTicket
from families.models import Family
from families.services import create_family_with_members
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestRegistrationSubmission(E2ETestBase, TestDataMixin):
    """Public submission form: unauthenticated, materializes a pending
    registration, and the resulting child must not be checkable in yet."""

    def setup_method(self):
        self.setup_driver()
        self.test_event, self.test_session = self.create_test_session(
            name="Registration E2E Session", is_active=True
        )
        self.test_user = self.create_test_user(
            username="registrationE2E", password="testpass123"
        )

    def teardown_method(self):
        Registration.objects.filter(event=self.test_event).delete()
        self.cleanup_test_data(
            users=[self.test_user],
            sessions=[self.test_session],
            events=[self.test_event],
        )
        self.teardown_driver()

    def test_submit_creates_pending_registration_not_yet_checkable(self):
        register_url = f"{self.config['frontend_url']}/register/{self.test_event.id}"
        self.driver.get(register_url)

        self.wait_for_element(By.ID, "contact-email").send_keys(
            "e2e-guardian@example.com"
        )
        self.wait_for_element(By.ID, "parent-name-0").send_keys("E2E Guardian")
        self.wait_for_element(By.ID, "child-first-name-0").send_keys("E2EChild")
        self.wait_for_element(By.ID, "child-last-name-0").send_keys("Pending")
        self.wait_for_element(By.ID, "child-birthdate-0").send_keys("01012018")

        self.wait_and_click(By.CSS_SELECTOR, "[data-testid='register-submit-button']")

        self.wait_for_element(By.CSS_SELECTOR, "h1")
        assert Registration.objects.filter(
            event=self.test_event, contact_email="e2e-guardian@example.com"
        ).exists()

        registration = Registration.objects.get(
            event=self.test_event, contact_email="e2e-guardian@example.com"
        )
        assert registration.status == Registration.Status.PENDING_VERIFICATION

        child = registration.family.children.get(first_name="E2EChild")
        assert self.login(self.test_user.username, "testpass123")
        checkin_url = f"{self.config['frontend_url']}/checkin"
        self.driver.get(checkin_url)
        self.expand_all_visible_family_rows()

        # However the pending state is surfaced in the UI, the underlying
        # check_in endpoint must refuse — this is the property that matters.
        response = self._authenticated_check_in(child)
        assert response.status_code == 400, response.text

    def _authenticated_check_in(self, child):
        """POST /api/checkins/check_in/ using the already-logged-in browser
        session's cookies. In split-origin dev (frontend :5173, backend
        :8000), the session/CSRF cookies Django set live on the backend's
        origin, not whatever origin the driver is currently on — so briefly
        navigate there to read them via get_cookies() before making the
        request."""
        import requests

        self.driver.get(f"{self.config['backend_url']}/api/auth/check/")
        session_cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
        return requests.post(
            f"{self.config['backend_url']}/api/checkins/check_in/",
            json={"child": str(child.id), "session": str(self.test_session.id)},
            cookies=session_cookies,
            headers={"X-CSRFToken": session_cookies.get("csrftoken", "")},
        )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestRegistrationVerifyAndCheckin(E2ETestBase, TestDataMixin):
    """Confirmed registrations must become checkable in immediately."""

    def setup_method(self):
        self.setup_driver()
        self.test_event, self.test_session = self.create_test_session(
            name="Registration Verify E2E Session", is_active=True
        )
        self.test_user = self.create_test_user(
            username="registrationVerifyE2E", password="testpass123"
        )

        family = create_family_with_members(
            last_name="E2EVerify",
            parents_data=[{"first_name": "Verify", "relationship_type": "OTHER"}],
            children_data=[{"first_name": "E2EChild", "last_name": "Confirmed"}],
        )
        self.token = generate_verification_token()
        self.registration = Registration.objects.create(
            event=self.test_event,
            family=family,
            contact_email="e2e-verify@example.com",
            verification_token_hash=hash_token(self.token),
        )
        for attendee in list(family.parents.all()) + list(family.children.all()):
            EventTicket.objects.create(
                attendee=attendee, event=self.test_event, registration=self.registration
            )
        self.test_family = family

    def teardown_method(self):
        self.registration.delete()
        Family.objects.filter(pk=self.test_family.pk).delete()
        self.cleanup_test_data(
            users=[self.test_user],
            sessions=[self.test_session],
            events=[self.test_event],
        )
        self.teardown_driver()

    def test_verify_confirms_and_child_becomes_checkable(self):
        verify_url = f"{self.config['frontend_url']}/register/verify/{self.token}"
        self.driver.get(verify_url)

        self.wait_for_element(By.CSS_SELECTOR, "h1")
        self.registration.refresh_from_db()
        assert self.registration.status == Registration.Status.CONFIRMED

        assert self.login(self.test_user.username, "testpass123")
        self.driver.get(f"{self.config['frontend_url']}/checkin")
        self.expand_all_visible_family_rows()

        child = self.test_family.children.get(first_name="E2EChild")
        response = self._authenticated_check_in(child)
        assert response.status_code == 201, response.text

    def _authenticated_check_in(self, child):
        """See TestRegistrationSubmission._authenticated_check_in."""
        import requests

        self.driver.get(f"{self.config['backend_url']}/api/auth/check/")
        session_cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
        return requests.post(
            f"{self.config['backend_url']}/api/checkins/check_in/",
            json={"child": str(child.id), "session": str(self.test_session.id)},
            cookies=session_cookies,
            headers={"X-CSRFToken": session_cookies.get("csrftoken", "")},
        )
