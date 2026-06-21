from django.core import mail
from django.test import override_settings
from django.urls import reverse

from .base import RegressionBaseTestCase


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FEEDBACK_EMAIL_TO="owner@example.com",
    DEFAULT_FROM_EMAIL="noreply@example.com",
    FEEDBACK_EMAIL_SUBJECT_PREFIX="[Fisio Feedback]",
    FEEDBACK_INCLUDE_METADATA=True,
)
class FeedbackTests(RegressionBaseTestCase):
    def test_feedback_requires_login(self):
        response = self.client.post(reverse("feedback-submit"), {"message": "Algo quebrou"})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_logged_in_user_can_send_feedback(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.post(
            reverse("feedback-submit"),
            {
                "feedback_type": "bug",
                "message": "O calendario nao carregou.",
                "source_page": "/forms/calendario/?dia=2026-06-21",
            },
            HTTP_USER_AGENT="TestBrowser/1.0",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["owner@example.com"])
        self.assertEqual(email.from_email, "noreply@example.com")
        self.assertIn("[Fisio Feedback] Erro", email.subject)
        self.assertIn("O calendario nao carregou.", email.body)
        self.assertIn("/forms/calendario/?dia=2026-06-21", email.body)
        self.assertIn(user.username, email.body)
        self.assertIn("TestBrowser/1.0", email.body)

    def test_feedback_rejects_empty_message(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.post(reverse("feedback-submit"), {"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["ok"], False)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(FEEDBACK_EMAIL_TO="")
    def test_feedback_requires_recipient_configuration(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.post(reverse("feedback-submit"), {"message": "Mensagem valida"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["ok"], False)
        self.assertEqual(len(mail.outbox), 0)
