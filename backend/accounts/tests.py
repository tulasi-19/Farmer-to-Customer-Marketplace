from django.test import TestCase
from rest_framework.test import APIClient

from common.test_utils import PASSWORD, make_user


class AuthTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def _register(self, **over):
        data = {'username': 'ravi', 'email': 'ravi@example.com', 'password': PASSWORD, 'role': 'farmer'}
        data.update(over)
        return self.c.post('/api/v1/auth/register/', data, format='json')

    def test_register_farmer_and_customer(self):
        self.assertEqual(self._register().status_code, 201)
        self.assertEqual(self._register(username='sita', email='s@example.com', role='customer').status_code, 201)

    def test_cannot_register_as_admin(self):
        r = self._register(role='admin')
        self.assertEqual(r.status_code, 400)

    def test_weak_password_and_duplicate_email_rejected(self):
        self.assertEqual(self._register(password='12345678').status_code, 400)
        self._register()
        self.assertEqual(self._register(username='other').status_code, 400)

    def test_login_returns_tokens_and_me_works(self):
        make_user('sita')
        r = self.c.post('/api/v1/auth/login/', {'username': 'sita', 'password': PASSWORD}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(self.c.get('/api/v1/auth/me/').data['username'], 'sita')

    def test_wrong_password_401_and_protected_endpoint_needs_token(self):
        make_user('sita')
        self.assertEqual(self.c.post('/api/v1/auth/login/', {'username': 'sita', 'password': 'nope'}).status_code, 401)
        self.assertEqual(self.c.get('/api/v1/auth/me/').status_code, 401)

    def test_user_cannot_promote_self_via_me(self):
        u = make_user('sita')
        self.c.force_authenticate(u)
        self.c.patch('/api/v1/auth/me/', {'role': 'admin', 'is_staff': True}, format='json')
        u.refresh_from_db()
        self.assertEqual(u.role, 'customer')
        self.assertFalse(u.is_staff)

    def test_refresh_and_logout_blacklists_token(self):
        make_user('sita')
        r = self.c.post('/api/v1/auth/login/', {'username': 'sita', 'password': PASSWORD}, format='json')
        refresh = r.data['refresh']
        self.assertEqual(self.c.post('/api/v1/auth/token/refresh/', {'refresh': refresh}, format='json').status_code, 200)
        r2 = self.c.post('/api/v1/auth/login/', {'username': 'sita', 'password': PASSWORD}, format='json')
        self.c.credentials(HTTP_AUTHORIZATION=f"Bearer {r2.data['access']}")
        self.assertEqual(self.c.post('/api/v1/auth/logout/', {'refresh': r2.data['refresh']}, format='json').status_code, 204)
        self.c.credentials()
        self.assertEqual(self.c.post('/api/v1/auth/token/refresh/', {'refresh': r2.data['refresh']}, format='json').status_code, 401)

    def test_role_guard_on_admin_routes(self):
        for role, expected in (('customer', 403), ('farmer', 403), ('admin', 200)):
            self.c.force_authenticate(make_user(f'u_{role}', role))
            self.assertEqual(self.c.get('/api/v1/admin/stats/').status_code, expected, role)
