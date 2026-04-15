from datetime import date, datetime, timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from forms.models import (
    CategoriaExercicio,
    ExercicioCatalogo,
    Paciente,
    Procedimento,
    ProcedimentoExercicio,
    Sessao,
    SessaoExercicio,
    TipoProcedimento,
)
from forms.services.scheduling_service import create_session_for_procedimento, generate_sessions_for_month_by_weekday, update_sessao


class RegressionBaseTestCase(TestCase):
    def create_user(self, *, with_exercise_permissions=False):
        user = User.objects.create_user(
            username=f"user_{User.objects.count() + 1}",
            email="user@example.com",
            password="testpass123",
        )
        if with_exercise_permissions:
            permissions = Permission.objects.filter(
                codename__in=["view_exerciciocatalogo", "view_categoriaexercicio"]
            )
            user.user_permissions.add(*permissions)
        return user

    def create_paciente(self, **overrides):
        index = Paciente.all_objects.count() + 1
        defaults = {
            "nome": f"Paciente {index}",
            "cpf": f"000.000.000-{index:02d}",
            "email": f"paciente{index}@example.com",
            "profissao": "Professor",
            "endereco": "Rua Principal, 123",
            "bairro": "Centro",
            "cep": "40000-000",
            "telefone": "7133333333",
            "celular": "71999999999",
            "telefone_comercial": "7132222222",
            "data_nascimento": date(1990, 1, min(index, 28)),
            "data_matricula": date.today(),
            "plano": "Particular",
            "observacoes": "",
        }
        defaults.update(overrides)
        return Paciente.objects.create(**defaults)

    def create_tipo_procedimento(self, **overrides):
        index = TipoProcedimento.all_objects.count() + 1
        defaults = {
            "nome": f"Tipo {index}",
            "habilita_exercicios": True,
        }
        defaults.update(overrides)
        return TipoProcedimento.objects.create(**defaults)

    def create_procedimento(self, **overrides):
        defaults = {
            "paciente": self.create_paciente(),
            "tipo_procedimento": self.create_tipo_procedimento(),
            "observacoes": "Procedimento base",
            "concluido": False,
        }
        defaults.update(overrides)
        return Procedimento.objects.create(**defaults)

    def create_categoria(self, **overrides):
        index = CategoriaExercicio.all_objects.count() + 1
        defaults = {
            "nome": f"Categoria {index}",
            "descricao": "Categoria de teste",
        }
        defaults.update(overrides)
        return CategoriaExercicio.objects.create(**defaults)

    def create_exercicio(self, **overrides):
        index = ExercicioCatalogo.all_objects.count() + 1
        defaults = {
            "nome": f"Exercicio {index}",
            "categoria": self.create_categoria(),
            "descricao": "Descricao do exercicio",
            "instrucoes": "Instrucoes de teste",
            "observacoes": "",
            "ativo": True,
        }
        defaults.update(overrides)
        return ExercicioCatalogo.objects.create(**defaults)

    def create_sessao(self, procedimento, *, days_offset=1, **overrides):
        data_hora = timezone.now() + timedelta(days=days_offset)
        defaults = {
            "data_hora": data_hora,
            "duracao_minutos": 60,
            "status": Sessao.STATUS_AGENDADA,
            "assinatura_confirmada": False,
            "observacoes": "",
        }
        defaults.update(overrides)
        return create_session_for_procedimento(procedimento, **defaults)


class CoreModelTests(RegressionBaseTestCase):
    def test_core_models_can_be_created_with_required_relations(self):
        paciente = self.create_paciente()
        tipo_procedimento = self.create_tipo_procedimento()
        procedimento = self.create_procedimento(
            paciente=paciente,
            tipo_procedimento=tipo_procedimento,
        )
        sessao = self.create_sessao(procedimento)
        categoria = self.create_categoria()
        exercicio = self.create_exercicio(categoria=categoria)

        self.assertIsNotNone(paciente.pk)
        self.assertIsNotNone(tipo_procedimento.pk)
        self.assertIsNotNone(procedimento.pk)
        self.assertIsNotNone(sessao.pk)
        self.assertIsNotNone(categoria.pk)
        self.assertIsNotNone(exercicio.pk)
        self.assertEqual(procedimento.paciente, paciente)
        self.assertEqual(procedimento.tipo_procedimento, tipo_procedimento)
        self.assertEqual(sessao.procedimento, procedimento)
        self.assertEqual(exercicio.categoria, categoria)


class RelationshipTests(RegressionBaseTestCase):
    def test_procedure_session_and_exercise_relationships_work_in_both_directions(self):
        procedimento = self.create_procedimento()
        sessao = self.create_sessao(procedimento)
        exercicio = self.create_exercicio()
        procedimento_exercicio = ProcedimentoExercicio.objects.create(
            procedimento=procedimento,
            exercicio=exercicio,
            ordem=1,
        )
        sessao_exercicio = SessaoExercicio.objects.create(
            sessao=sessao,
            exercicio=exercicio,
            ordem=1,
        )

        self.assertEqual(procedimento.sessoes.count(), 1)
        self.assertEqual(procedimento.procedimento_exercicios.count(), 1)
        self.assertEqual(sessao.sessao_exercicios.count(), 1)
        self.assertEqual(procedimento_exercicio.exercicio.categoria, exercicio.categoria)
        self.assertTrue(exercicio.procedimento_exercicios.filter(pk=procedimento_exercicio.pk).exists())
        self.assertTrue(exercicio.sessao_exercicios.filter(pk=sessao_exercicio.pk).exists())
        self.assertTrue(exercicio.categoria.exercicios.filter(pk=exercicio.pk).exists())
        self.assertTrue(procedimento.paciente.procedimentos.filter(pk=procedimento.pk).exists())


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


class SoftDeleteTests(RegressionBaseTestCase):
    def test_delete_route_marks_patient_inactive_without_removing_row(self):
        user = self.create_user()
        paciente = self.create_paciente()
        self.client.force_login(user)

        response = self.client.post(reverse("inscricao-delete", args=[paciente.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Paciente.objects.filter(pk=paciente.pk).exists())
        stored = Paciente.all_objects.get(pk=paciente.pk)
        self.assertFalse(stored.is_active)
        self.assertIsNotNone(stored.deleted_at)


class SessionLogicTests(RegressionBaseTestCase):
    def test_sessions_are_numbered_sequentially_in_chronological_order(self):
        procedimento = self.create_procedimento()

        terceira = self.create_sessao(procedimento, days_offset=3)
        primeira = self.create_sessao(procedimento, days_offset=1)
        segunda = self.create_sessao(procedimento, days_offset=2)

        terceira.refresh_from_db()
        primeira.refresh_from_db()
        segunda.refresh_from_db()

        numeros = list(
            procedimento.sessoes.order_by("data_hora").values_list("numero", flat=True)
        )

        self.assertEqual(numeros, [1, 2, 3])
        self.assertEqual(primeira.numero, 1)
        self.assertEqual(segunda.numero, 2)
        self.assertEqual(terceira.numero, 3)

        quarta = self.create_sessao(procedimento, days_offset=4)
        self.assertEqual(quarta.numero, 4)
        self.assertEqual(
            list(procedimento.sessoes.order_by("numero").values_list("numero", flat=True)),
            [1, 2, 3, 4],
        )


class SessionConflictTests(RegressionBaseTestCase):
    def test_single_booking_without_conflict_saves_successfully(self):
        procedimento = self.create_procedimento()
        inicio = timezone.make_aware(datetime(2026, 3, 18, 9, 0))

        sessao = create_session_for_procedimento(
            procedimento,
            data_hora=inicio,
            duracao_minutos=60,
        )

        self.assertTrue(Sessao.objects.filter(pk=sessao.pk).exists())
        self.assertEqual(sessao.duracao_minutos, 60)

    def test_single_booking_with_overlap_is_rejected(self):
        procedimento = self.create_procedimento()
        outro_procedimento = self.create_procedimento()
        create_session_for_procedimento(
            procedimento,
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 0)),
            duracao_minutos=60,
        )

        with self.assertRaisesMessage(ValidationError, "Conflito de horário"):
            create_session_for_procedimento(
                outro_procedimento,
                data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 30)),
                duracao_minutos=60,
            )

        self.assertEqual(Sessao.objects.count(), 1)

    def test_bulk_generation_saves_only_non_conflicting_sessions(self):
        procedimento = self.create_procedimento()
        conflicting_procedimento = self.create_procedimento()
        create_session_for_procedimento(
            conflicting_procedimento,
            data_hora=timezone.make_aware(datetime(2026, 3, 5, 9, 0)),
            duracao_minutos=60,
        )

        result = generate_sessions_for_month_by_weekday(
            procedimento,
            year=2026,
            month=3,
            weekdays=[3],
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("10:00", "%H:%M").time(),
        )

        self.assertEqual(len(result.created_sessions), 3)
        self.assertEqual(len(result.skipped_conflicts), 1)
        self.assertEqual(
            [timezone.localtime(value).strftime("%Y-%m-%d %H:%M") for value in result.skipped_conflicts],
            ["2026-03-05 09:00"],
        )

    def test_inactive_session_does_not_block_new_booking(self):
        procedimento = self.create_procedimento()
        existing = create_session_for_procedimento(
            procedimento,
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 0)),
            duracao_minutos=60,
        )
        existing.delete()

        nova = create_session_for_procedimento(
            self.create_procedimento(),
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 30)),
            duracao_minutos=60,
        )

        self.assertTrue(Sessao.objects.filter(pk=nova.pk).exists())

    def test_editing_existing_session_does_not_conflict_with_itself(self):
        procedimento = self.create_procedimento()
        sessao = create_session_for_procedimento(
            procedimento,
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 0)),
            duracao_minutos=60,
        )

        updated = update_sessao(
            sessao,
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 0)),
            duracao_minutos=60,
            status=Sessao.STATUS_AGENDADA,
            assinatura_confirmada=False,
            observacoes="Sem conflito consigo mesma",
        )

        self.assertEqual(updated.pk, sessao.pk)
        self.assertEqual(updated.observacoes, "Sem conflito consigo mesma")

    def test_single_booking_view_shows_warning_and_does_not_save_conflict(self):
        user = self.create_user()
        procedimento = self.create_procedimento()
        create_session_for_procedimento(
            self.create_procedimento(),
            data_hora=timezone.make_aware(datetime(2026, 3, 18, 9, 0)),
            duracao_minutos=60,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("procedure-session-add", args=[procedimento.pk]),
            {
                "data_hora": "2026-03-18T09:30",
                "hora_final": "10:30",
                "status": Sessao.STATUS_AGENDADA,
                "observacoes": "",
            },
            follow=True,
        )

        rendered_messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(any("Conflito de horário" in message for message in rendered_messages))
        self.assertEqual(procedimento.sessoes.count(), 0)

    def test_bulk_booking_view_reports_partial_success(self):
        user = self.create_user()
        procedimento = self.create_procedimento()
        create_session_for_procedimento(
            self.create_procedimento(),
            data_hora=timezone.make_aware(datetime(2026, 3, 5, 9, 0)),
            duracao_minutos=60,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("procedure-bulk-schedule", args=[procedimento.pk]),
            {
                "referencia_mes": "2026-03",
                "dias_semana": ["3"],
                "hora_inicial": "09:00",
                "hora_final": "10:00",
            },
            follow=True,
        )

        self.assertContains(response, "3 sessão(ões) criada(s) com sucesso para este procedimento.")
        self.assertContains(response, "1 sessão(ões) foram ignoradas por conflito de horário")
        self.assertEqual(procedimento.sessoes.count(), 3)


class ExerciseTests(RegressionBaseTestCase):
    def test_exercises_can_be_assigned_to_a_session_via_the_update_view(self):
        user = self.create_user()
        procedimento = self.create_procedimento(
            tipo_procedimento=self.create_tipo_procedimento(habilita_exercicios=True)
        )
        sessao = self.create_sessao(procedimento)
        exercicio = self.create_exercicio()
        ProcedimentoExercicio.objects.create(
            procedimento=procedimento,
            exercicio=exercicio,
            ordem=1,
            series="3",
            repeticoes="10",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("session-exercise-update", args=[sessao.pk]),
            {"exercicios": [exercicio.pk]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SessaoExercicio.objects.filter(sessao=sessao, exercicio=exercicio).exists())
        assigned = SessaoExercicio.objects.get(sessao=sessao, exercicio=exercicio)
        self.assertEqual(assigned.ordem, 1)
        self.assertEqual(assigned.series, "3")
        self.assertTrue(sessao.sessao_exercicios.filter(pk=assigned.pk).exists())
