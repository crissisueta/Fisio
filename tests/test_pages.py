from django.urls import reverse

from forms.models import Procedimento

from .base import RegressionBaseTestCase


class PageLoadTests(RegressionBaseTestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)

    def test_core_logged_in_pages_load(self):
        user = self.create_user()
        procedimento = self.create_procedimento()
        self.client.force_login(user)

        urls = [
            reverse("calendar-dashboard"),
            reverse("procedure-list"),
            reverse("procedure-detail", args=[procedimento.pk]),
            reverse("procedure-bulk-schedule", args=[procedimento.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_calendar_dashboard_renders_new_procedure_form(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.get(reverse("calendar-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Procedimento")
        self.assertContains(response, "Crie um procedimento diretamente a partir da agenda")

    def test_procedure_list_no_longer_shows_new_procedure_button(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.get(reverse("procedure-list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "+ Novo Procedimento")

    def test_calendar_dashboard_can_create_procedure_with_initial_session(self):
        user = self.create_user()
        paciente = self.create_paciente()
        tipo_procedimento = self.create_tipo_procedimento()
        self.client.force_login(user)

        response = self.client.post(
            reverse("calendar-dashboard"),
            {
                "paciente": paciente.pk,
                "tipo_procedimento": tipo_procedimento.pk,
                "observacoes": "Criado pelo calendario",
                "concluido": "",
                "modo_agendamento": "unico",
                "data_sessao_inicial": "2026-04-20",
                "hora_sessao_inicial": "09:00",
                "hora_fim_sessao_inicial": "10:00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        procedimento = Procedimento.objects.get(observacoes="Criado pelo calendario")
        self.assertRedirects(response, reverse("procedure-detail", args=[procedimento.pk]))
        self.assertEqual(procedimento.paciente, paciente)
        self.assertEqual(procedimento.tipo_procedimento, tipo_procedimento)
        self.assertEqual(procedimento.sessoes.count(), 1)

    def test_exercise_management_pages_load_for_authorized_user(self):
        user = self.create_user(with_exercise_permissions=True)
        self.client.force_login(user)

        urls = [
            reverse("exercise-list"),
            reverse("exercise-category-list"),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

