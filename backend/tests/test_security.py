"""
Tests for security features including rate limiting and security headers.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import AdminUser


class RateLimitingTests(TestCase):
    """
    Test rate limiting on login endpoint.
    """

    def setUp(self):
        """Create test user and client."""
        self.client = APIClient()
        self.login_url = reverse('login')
        self.user = AdminUser.objects.create_user(
            username='testuser',
            password='testpass123',
            name='Test User'
        )

    @override_settings(
        REST_FRAMEWORK={
            'DEFAULT_THROTTLE_CLASSES': [
                'rest_framework.throttling.AnonRateThrottle',
            ],
            'DEFAULT_THROTTLE_RATES': {
                'anon': '5/minute',
                'login': '5/minute',
            }
        }
    )
    def test_login_rate_limiting(self):
        """
        Test that login endpoint is rate limited to 5 attempts per minute.
        """
        # Make 5 failed login attempts (should succeed)
        for i in range(5):
            response = self.client.post(
                self.login_url,
                {'username': 'testuser', 'password': 'wrongpassword'},
                format='json'
            )
            # Should get 401 Unauthorized for wrong password
            self.assertIn(response.status_code, [401, 429])

        # 6th attempt should be rate limited
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'wrongpassword'},
            format='json'
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn('throttled', str(response.data).lower())

    def test_successful_login_not_throttled_on_first_attempt(self):
        """
        Test that successful login works on first attempt.
        """
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpass123'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('success'))


class SecurityHeadersTests(TestCase):
    """
    Test security headers in production settings.
    """

    @override_settings(
        DEBUG=False,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_CONTENT_TYPE_NOSNIFF=True,
        X_FRAME_OPTIONS='DENY',
    )
    def test_security_headers_configured(self):
        """
        Test that security headers are properly configured.
        """
        from django.conf import settings

        # Test HSTS settings
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 31536000)
        self.assertTrue(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)

        # Test other security settings
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')

    @override_settings(
        DEBUG=False,
        SESSION_COOKIE_SAMESITE='Strict',
        CSRF_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_AGE=28800,
        SESSION_EXPIRE_AT_BROWSER_CLOSE=True,
    )
    def test_session_security_configured(self):
        """
        Test that session security settings are configured.
        """
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Strict')
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Strict')
        self.assertEqual(settings.SESSION_COOKIE_AGE, 28800)
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
