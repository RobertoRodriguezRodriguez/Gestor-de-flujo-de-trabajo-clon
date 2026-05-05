from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .helpers import make_user, get_access_token


class TokenObtainTest(APITestCase):
    def setUp(self):
        self.user = make_user(password='securepass1!')
        self.url = reverse('api_token_obtain')

    def test_valid_credentials_return_tokens(self):
        response = self.client.post(self.url, {
            'email': self.user.email,
            'password': 'securepass1!',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_wrong_password_returns_401(self):
        response = self.client.post(self.url, {
            'email': self.user.email,
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        response = self.client.post(self.url, {
            'email': 'nobody@example.com',
            'password': 'anypassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_password_returns_400(self):
        response = self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_returns_401(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {
            'email': self.user.email,
            'password': 'securepass1!',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        _, self.refresh_token = get_access_token(self.user)
        self.url = reverse('api_token_refresh')

    def test_valid_refresh_returns_new_access_token(self):
        response = self.client.post(self.url, {'refresh': self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_invalid_token_returns_401(self):
        response = self.client.post(self.url, {'refresh': 'not-a-valid-token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRevokeTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.access_token, self.refresh_token = get_access_token(self.user)
        self.url = reverse('api_token_revoke')

    def test_revoke_valid_token_returns_204(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.url, {'refresh': self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_revoke_without_auth_returns_401(self):
        response = self.client.post(self.url, {'refresh': self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoke_without_refresh_token_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revoked_token_cannot_be_refreshed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.client.post(self.url, {'refresh': self.refresh_token})
        # Try to use the revoked refresh token
        refresh_url = reverse('api_token_refresh')
        response = self.client.post(refresh_url, {'refresh': self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.access_token, _ = get_access_token(self.user)
        self.url = reverse('api_me')

    def test_authenticated_user_gets_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['name'], self.user.name)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_updates_name(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.patch(self.url, {'name': 'New Name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'New Name')

    def test_email_is_read_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.client.patch(self.url, {'email': 'hacked@example.com'})
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email, 'hacked@example.com')

    def test_is_premium_is_read_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.client.patch(self.url, {'is_premium': True})
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
