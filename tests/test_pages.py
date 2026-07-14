from django.urls import reverse

from forms.models import Procedimento

from .base import RegressionBaseTestCase


class PageLoadTests(RegressionBaseTestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-feedback-widget')

    def test_feedback_widget_renders_for_authenticated_user(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-feedback-widget')
        self.assertContains(response, "Reportar erro")

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

    def test_patient_list_paginates_one_hundred_per_page(self):
        user = self.create_user()
        for index in range(101):
            self.create_paciente(nome=f"Paciente Lista {index:03d}")
        self.client.force_login(user)

        first_page = self.client.get(reverse("inscricao-list"))
        second_page = self.client.get(reverse("inscricao-list"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["paginator"].per_page, 100)
        self.assertEqual(len(first_page.context["fichas"]), 100)
        self.assertEqual(len(second_page.context["fichas"]), 1)

    def test_patient_list_search_filters_by_query(self):
        user = self.create_user()
        self.create_paciente(nome="Ana Pesquisa", email="ana.pesquisa@example.com")
        self.create_paciente(nome="Bruno Fora", email="bruno.fora@example.com")
        self.client.force_login(user)

        response = self.client.get(reverse("inscricao-list"), {"q": "ana.pesquisa"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["search_query"], "ana.pesquisa")
        self.assertContains(response, "Ana Pesquisa")
        self.assertNotContains(response, "Bruno Fora")
        self.assertContains(response, 'value="ana.pesquisa"')

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
