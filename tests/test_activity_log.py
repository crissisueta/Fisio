import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import ActivityLog
from tests.base import RegressionBaseTestCase
from tests.test_importacao import _tracking_xlsx_for_patient


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ActivityLogPageTests(RegressionBaseTestCase):
    def create_staff_user(self, **overrides):
        defaults = {
            "username": f"staff_{User.objects.count() + 1}",
            "password": "testpass123",
            "is_staff": True,
        }
        defaults.update(overrides)
        return User.objects.create_user(**defaults)

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.get(reverse("admin-activity"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_authenticated_non_admin_access_returns_403(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.get(reverse("admin-activity"))

        self.assertEqual(response.status_code, 403)

    def test_staff_or_superuser_access_succeeds(self):
        users = [
            self.create_staff_user(username="staff_user", is_staff=True),
            self.create_staff_user(username="super_user", is_staff=False, is_superuser=True),
        ]

        for user in users:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse("admin-activity"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Atividades do sistema")
                self.client.logout()

    def test_entries_are_ordered_newest_first(self):
        staff = self.create_staff_user()
        older = ActivityLog.objects.create(user=staff, event_type="test.older", message="atividade antiga")
        newer = ActivityLog.objects.create(user=staff, event_type="test.newer", message="atividade recente")
        ActivityLog.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(hours=1))
        ActivityLog.objects.filter(pk=newer.pk).update(created_at=timezone.now())
        self.client.force_login(staff)

        response = self.client.get(reverse("admin-activity"))

        entries = list(response.context["activity_entries"])
        self.assertEqual([entry.pk for entry in entries], [newer.pk, older.pk])

    def test_pagination_uses_fifty_entries_per_page(self):
        staff = self.create_staff_user()
        for index in range(51):
            ActivityLog.objects.create(user=staff, event_type="test.pagination", message=f"atividade {index:02d}")
        self.client.force_login(staff)

        first_page = self.client.get(reverse("admin-activity"))
        second_page = self.client.get(reverse("admin-activity"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["paginator"].per_page, 50)
        self.assertEqual(len(first_page.context["activity_entries"]), 50)
        self.assertTrue(first_page.context["page_obj"].has_next())
        self.assertEqual(len(second_page.context["activity_entries"]), 1)

    def test_successful_spreadsheet_import_creates_one_activity_entry(self):
        staff = self.create_staff_user(first_name="João", last_name="Silva")
        self.client.force_login(staff)
        upload = SimpleUploadedFile(
            "historico.xlsx",
            _tracking_xlsx_for_patient("Paciente Log", date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": upload,
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ActivityLog.objects.count(), 1)
        entry = ActivityLog.objects.get()
        self.assertEqual(entry.user, staff)
        self.assertEqual(entry.actor_name, "João Silva")
        self.assertEqual(entry.event_type, "spreadsheet_import.success")
        self.assertEqual(entry.level, ActivityLog.LEVEL_SUCCESS)
        self.assertEqual(entry.message, "importou 1 planilha")
        self.assertEqual(entry.metadata["file_count"], 1)

    def test_failed_spreadsheet_import_creates_one_safe_error_entry(self):
        staff = self.create_staff_user()
        self.client.force_login(staff)
        upload = SimpleUploadedFile(
            "falha.xlsx",
            b"nao e uma planilha valida",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": upload,
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ActivityLog.objects.count(), 1)
        entry = ActivityLog.objects.get()
        self.assertEqual(entry.event_type, "spreadsheet_import.failed")
        self.assertEqual(entry.level, ActivityLog.LEVEL_ERROR)
        self.assertEqual(entry.message, "teve falha ao importar uma planilha")
        self.assertNotIn("nao e uma planilha valida", entry.message)
        self.assertNotIn("nao e uma planilha valida", json.dumps(entry.metadata))

    def test_sensitive_error_details_are_not_exposed_on_activity_page(self):
        staff = self.create_staff_user()
        self.client.force_login(staff)
        upload = SimpleUploadedFile(
            "segredo.xlsx",
            _tracking_xlsx_for_patient("Paciente Segredo", date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        with (
            patch(
                "importacao.services.read_exercise_tracking_spreadsheet",
                side_effect=RuntimeError("token-secreto-123 traceback privado"),
            ),
            patch("importacao.services.logger.exception"),
        ):
            self.client.post(
                reverse("spreadsheet-import"),
                {
                    "arquivo": upload,
                    "update_existing": "on",
                    "create_related": "on",
                },
                follow=True,
            )

        response = self.client.get(reverse("admin-activity"))

        self.assertEqual(ActivityLog.objects.count(), 1)
        self.assertContains(response, "teve falha ao importar uma planilha")
        self.assertNotContains(response, "token-secreto-123")
        self.assertNotContains(response, "traceback privado")

    def test_activity_page_url_is_not_added_to_visible_navigation(self):
        staff = self.create_staff_user()
        self.client.force_login(staff)
        hidden_path = reverse("admin-activity")

        for url in [reverse("index"), reverse("calendar-dashboard"), reverse("inscricao-list")]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, hidden_path)
                self.assertNotContains(response, "Atividades do sistema")
