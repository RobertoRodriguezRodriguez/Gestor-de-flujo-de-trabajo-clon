from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, UserSession


class UserGetInitialsTest(TestCase):
    def test_two_words(self):
        user = User(name='Carla García')
        self.assertEqual(user.get_initials(), 'CG')

    def test_one_word(self):
        user = User(name='Carla')
        self.assertEqual(user.get_initials(), 'CA')

    def test_single_char(self):
        user = User(name='A')
        self.assertEqual(user.get_initials(), 'A')

    def test_more_than_two_words_uses_first_two(self):
        user = User(name='María del Carmen')
        self.assertEqual(user.get_initials(), 'MD')

    def test_lowercase_returns_uppercase(self):
        user = User(name='ana perez')
        self.assertEqual(user.get_initials(), 'AP')


class UserManagerTest(TestCase):
    def test_create_user_basic(self):
        user = User.objects.create_user(
            email='test@example.com', name='Test User', password='securepass1!'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.name, 'Test User')
        self.assertTrue(user.check_password('securepass1!'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_normalizes_email_domain(self):
        # Django normalizes only the domain part (RFC 5321), not the local part
        user = User.objects.create_user(
            email='TEST@EXAMPLE.COM', name='Test', password='pass'
        )
        self.assertEqual(user.email, 'TEST@example.com')

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', name='Test', password='pass')

    def test_create_user_default_role_is_member(self):
        user = User.objects.create_user(
            email='member@example.com', name='Member', password='pass'
        )
        self.assertEqual(user.role, 'member')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com', name='Admin', password='pass'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'admin')

    def test_user_str(self):
        user = User.objects.create_user(
            email='str@example.com', name='Sting Ray', password='pass'
        )
        self.assertIn('Sting Ray', str(user))
        self.assertIn('str@example.com', str(user))


class UserOnlineStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='online@example.com', name='Online User', password='pass'
        )

    def test_no_sessions_returns_offline(self):
        self.assertEqual(self.user.get_online_status(), 'offline')

    def test_recent_session_returns_online(self):
        session = UserSession.objects.create(
            user=self.user,
            session_key='key-online-1',
            ip_address='127.0.0.1',
        )
        UserSession.objects.filter(pk=session.pk).update(
            last_seen=timezone.now() - timedelta(minutes=2)
        )
        self.assertEqual(self.user.get_online_status(), 'online')

    def test_session_6_minutes_ago_returns_away(self):
        session = UserSession.objects.create(
            user=self.user,
            session_key='key-away-1',
            ip_address='127.0.0.1',
        )
        UserSession.objects.filter(pk=session.pk).update(
            last_seen=timezone.now() - timedelta(minutes=10)
        )
        self.assertEqual(self.user.get_online_status(), 'away')

    def test_session_31_minutes_ago_returns_offline(self):
        session = UserSession.objects.create(
            user=self.user,
            session_key='key-offline-1',
            ip_address='127.0.0.1',
        )
        UserSession.objects.filter(pk=session.pk).update(
            last_seen=timezone.now() - timedelta(minutes=35)
        )
        self.assertEqual(self.user.get_online_status(), 'offline')


class UserSessionDeviceInfoTest(TestCase):
    def _make_session(self, ua):
        return UserSession(user_agent=ua, session_key='test', ip_address='127.0.0.1')

    def test_chrome_windows_desktop(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['browser'], 'Chrome')
        self.assertEqual(info['os'], 'Windows')
        self.assertFalse(info['is_mobile'])

    def test_firefox_linux(self):
        ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['browser'], 'Firefox')
        self.assertEqual(info['os'], 'Linux')
        self.assertFalse(info['is_mobile'])

    def test_safari_iphone_mobile(self):
        ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['os'], 'iPhone')
        self.assertTrue(info['is_mobile'])

    def test_edge_browser(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/120.0 Safari/537.36'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['browser'], 'Edge')

    def test_android_mobile(self):
        ua = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) Mobile Chrome/120.0'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['os'], 'Android')
        self.assertTrue(info['is_mobile'])

    def test_macos_safari(self):
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15'
        info = self._make_session(ua).get_device_info()
        self.assertEqual(info['browser'], 'Safari')
        self.assertEqual(info['os'], 'macOS')

    def test_unknown_browser_and_os(self):
        info = self._make_session('totally-unknown-agent').get_device_info()
        self.assertEqual(info['browser'], 'Navegador')
        self.assertEqual(info['os'], 'Dispositivo desconocido')
        self.assertFalse(info['is_mobile'])
