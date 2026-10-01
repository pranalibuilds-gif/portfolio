from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView


class ProtectedProbeView(APIView):
    def get(self, request):
        return Response({'detail': 'authorized'})


class JwtAuthenticationEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='cms-admin',
            password='Strong-local-test-password-42',
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            '/api/auth/token/',
            {
                'username': self.user.username,
                'password': 'Strong-local-test-password-42',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            '/api/auth/token/',
            {'username': self.user.username, 'password': 'incorrect'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_login_requires_credentials(self):
        response = self.client.post('/api/auth/token/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_returns_new_access_token(self):
        login_response = self.client.post(
            '/api/auth/token/',
            {
                'username': self.user.username,
                'password': 'Strong-local-test-password-42',
            },
            format='json',
        )

        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': login_response.data['refresh']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_refresh_rejects_invalid_token(self):
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': 'invalid-token'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_requires_token(self):
        response = self.client.post('/api/auth/token/refresh/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_protected_view_rejects_anonymous_request(self):
        request = APIRequestFactory().get('/protected/')

        response = ProtectedProbeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_view_rejects_authenticated_non_staff_user(self):
        login_response = self.client.post(
            '/api/auth/token/',
            {
                'username': self.user.username,
                'password': 'Strong-local-test-password-42',
            },
            format='json',
        )
        request = APIRequestFactory().get(
            '/protected/',
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        response = ProtectedProbeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_protected_view_allows_staff_user(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        login_response = self.client.post(
            '/api/auth/token/',
            {
                'username': self.user.username,
                'password': 'Strong-local-test-password-42',
            },
            format='json',
        )
        request = APIRequestFactory().get(
            '/protected/',
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        response = ProtectedProbeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
