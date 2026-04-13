from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class WorkspaceLoginSessionTests(TestCase):
    def test_login_sets_session_to_expire_after_24_hours(self):
        User.objects.create_user(username="session-user", password="testpass123")

        response = self.client.post(
            reverse("login"),
            {"username": "session-user", "password": "testpass123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), 60 * 60 * 24)
