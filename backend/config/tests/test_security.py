from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from config.settings import _mailers_for_environment, _secret_key_for_environment


class CorsAndSecurityConfigurationTests(TestCase):
    def test_local_frontend_origin_is_allowed_for_preflight(self):
        response = self.client.options(
            '/api/auth/token/',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            'http://localhost:5173',
        )
        self.assertIn('POST', response['Access-Control-Allow-Methods'])
        self.assertIn('authorization', response['Access-Control-Allow-Headers'])

    def test_unconfigured_origin_is_not_allowed(self):
        response = self.client.options(
            '/api/auth/token/',
            HTTP_ORIGIN='https://untrusted.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        )

        self.assertNotIn('Access-Control-Allow-Origin', response)

    def test_default_security_headers_are_present(self):
        response = self.client.get('/api/auth/token/')

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(
            response['Referrer-Policy'],
            'strict-origin-when-cross-origin',
        )

    def test_development_settings_do_not_force_https_or_enable_hsts(self):
        self.assertFalse(settings.SECURE_SSL_REDIRECT)
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)

    def test_cors_is_allowlist_based(self):
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)
        self.assertFalse(settings.CORS_ALLOW_CREDENTIALS)

    def test_development_secret_fallback_is_limited_to_debug_mode(self):
        self.assertEqual(
            _secret_key_for_environment(True, None),
            'django-insecure-local-development-key',
        )
        with self.assertRaises(ImproperlyConfigured):
            _secret_key_for_environment(False, None)
        with self.assertRaises(ImproperlyConfigured):
            _secret_key_for_environment(False, 'django-insecure-weak-key')

    def test_production_requires_a_strong_unique_secret(self):
        secret = 'phase-six-production-secret-key-with-many-unique-characters-493!'
        self.assertEqual(_secret_key_for_environment(False, secret), secret)
        with self.assertRaises(ImproperlyConfigured):
            _secret_key_for_environment(False, 'too-short')

    def test_email_backend_defaults_match_environment(self):
        development_mailer = _mailers_for_environment(True, {})
        production_mailer = _mailers_for_environment(False, {})

        self.assertEqual(
            development_mailer['default']['BACKEND'],
            'django.core.mail.backends.console.EmailBackend',
        )
        self.assertEqual(
            production_mailer['default']['BACKEND'],
            'django.core.mail.backends.smtp.EmailBackend',
        )
        self.assertEqual(
            production_mailer['default']['OPTIONS']['host'],
            'localhost',
        )

    def test_smtp_tls_modes_are_mutually_exclusive(self):
        with self.assertRaises(ImproperlyConfigured):
            _mailers_for_environment(
                False,
                {'EMAIL_USE_TLS': 'True', 'EMAIL_USE_SSL': 'True'},
            )

    def test_authenticated_production_smtp_requires_tls(self):
        with self.assertRaises(ImproperlyConfigured):
            _mailers_for_environment(
                False,
                {'EMAIL_HOST_USER': 'mailer', 'EMAIL_HOST_PASSWORD': 'secret'},
            )

        with self.assertRaises(ImproperlyConfigured):
            _mailers_for_environment(
                False,
                {'EMAIL_HOST_USER': 'mailer'},
            )

        secure_mailer = _mailers_for_environment(
            False,
            {
                'EMAIL_HOST_USER': 'mailer',
                'EMAIL_HOST_PASSWORD': 'secret',
                'EMAIL_USE_TLS': 'True',
            },
        )
        self.assertTrue(secure_mailer['default']['OPTIONS']['use_tls'])
