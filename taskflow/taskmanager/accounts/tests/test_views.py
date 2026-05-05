from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import User

# Use simple static storage so collectstatic is not required during tests.
STATIC_OVERRIDE = override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)

# Patch Django 5.0.4 + Python 3.14 incompatibility: copy(super()) returns
# the super proxy object instead of a new instance, so setting attributes on it fails.
from django.template.context import BaseContext as _BaseContext


def _py314_context_copy(self):
    cls = type(self)
    new_obj = cls.__new__(cls)
    new_obj.__dict__.update(self.__dict__)
    new_obj.dicts = self.dicts[:]
    return new_obj


_BaseContext.__copy__ = _py314_context_copy


def make_user(email='user@example.com', name='Test User', password='securepass1!'):
    return User.objects.create_user(email=email, name=name, password=password)


@STATIC_OVERRIDE
class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_login_page_returns_200(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_redirect_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'user@example.com',
            'password': 'securepass1!',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_wrong_password_stays_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'user@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_nonexistent_user_stays_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'nobody@example.com',
            'password': 'pass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_redirected_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_next_param_respected(self):
        response = self.client.post(
            reverse('login') + '?next=/profile/',
            {'username': 'user@example.com', 'password': 'securepass1!'},
        )
        self.assertRedirects(response, '/profile/')

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse('login'), {
            'username': 'user@example.com',
            'password': 'securepass1!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


@STATIC_OVERRIDE
class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_returns_200(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_valid_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse('register'), {
            'name': 'New User',
            'email': 'newuser@example.com',
            'password1': 'securepass1!',
            'password2': 'securepass1!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_duplicate_email_fails(self):
        make_user(email='existing@example.com')
        response = self.client.post(reverse('register'), {
            'name': 'Another',
            'email': 'existing@example.com',
            'password1': 'securepass1!',
            'password2': 'securepass1!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)

    def test_mismatched_passwords_fails(self):
        response = self.client.post(reverse('register'), {
            'name': 'Test',
            'email': 'mismatch@example.com',
            'password1': 'securepass1!',
            'password2': 'differentpass!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='mismatch@example.com').exists())

    def test_authenticated_user_redirected_from_register(self):
        user = make_user(email='already@example.com')
        self.client.force_login(user)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('dashboard'))


@STATIC_OVERRIDE
class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_logout_clears_session(self):
        self.client.force_login(self.user)
        self.client.get(reverse('logout'))
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")
