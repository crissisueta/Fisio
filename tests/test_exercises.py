from datetime import date, datetime
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from forms.exercicios.services.monthly_tracking import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_RED,
    DAY_FUTURE,
    DAY_PAST,
    DAY_TODAY,
    build_monthly_exercise_tracking_table,
)
from forms.models import ProcedimentoExercicio, Sessao, SessaoExercicio

from .base import RegressionBaseTestCase


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

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_color_states_are_computed_from_patient_history(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        categoria = self.create_categoria(nome="Solo")
        red_exercise = self.create_exercicio(nome="Exercicio vermelho", categoria=categoria)
        blue_exercise = self.create_exercicio(nome="Exercicio azul", categoria=categoria)
        black_exercise = self.create_exercicio(nome="Exercicio preto", categoria=categoria)

        for exercise in (red_exercise, blue_exercise, black_exercise):
            ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercise)

        old_session = self.create_completed_session(procedimento, datetime(2026, 3, 1, 9, 0))
        last_session = self.create_completed_session(procedimento, datetime(2026, 5, 1, 9, 0))
        cancelled_session = self.create_session_with_status(
            procedimento,
            datetime(2026, 5, 5, 9, 0),
            Sessao.STATUS_CANCELADA,
        )
        SessaoExercicio.objects.create(sessao=old_session, exercicio=blue_exercise)
        SessaoExercicio.objects.create(sessao=last_session, exercicio=red_exercise)
        SessaoExercicio.objects.create(sessao=cancelled_session, exercicio=blue_exercise)

        table = build_monthly_exercise_tracking_table(paciente, date(2026, 5, 1))
        rows = self.exercise_rows_by_name(table)

        self.assertEqual(rows["Exercicio vermelho"].color_state, COLOR_RED)
        self.assertEqual(rows["Exercicio azul"].color_state, COLOR_BLUE)
        self.assertEqual(rows["Exercicio preto"].color_state, COLOR_BLACK)

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_changes_performed_days_when_month_changes(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Ponte")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)

        april_session = self.create_completed_session(procedimento, datetime(2026, 4, 10, 9, 0))
        may_session = self.create_completed_session(procedimento, datetime(2026, 5, 2, 9, 0))
        SessaoExercicio.objects.create(sessao=april_session, exercicio=exercicio)
        SessaoExercicio.objects.create(sessao=may_session, exercicio=exercicio)

        april_table = build_monthly_exercise_tracking_table(paciente, "2026-04")
        may_table = build_monthly_exercise_tracking_table(paciente, "2026-05")

        self.assertEqual(self.performed_days(self.exercise_rows_by_name(april_table)["Ponte"]), [10])
        self.assertEqual(self.performed_days(self.exercise_rows_by_name(may_table)["Ponte"]), [2])

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_marks_scheduled_session_exercises(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        explicit_exercise = self.create_exercicio(nome="Marcado na sessao")
        default_exercise = self.create_exercicio(nome="Planejado no procedimento")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=default_exercise)

        explicit_session = self.create_session_with_status(
            procedimento,
            datetime(2026, 5, 8, 9, 0),
            Sessao.STATUS_AGENDADA,
        )
        fallback_session = self.create_session_with_status(
            procedimento,
            datetime(2026, 5, 9, 9, 0),
            Sessao.STATUS_AGENDADA,
        )
        SessaoExercicio.objects.create(sessao=explicit_session, exercicio=explicit_exercise)

        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        rows = self.exercise_rows_by_name(table)

        self.assertEqual(self.performed_days(rows["Marcado na sessao"]), [8])
        self.assertEqual(self.performed_days(rows["Planejado no procedimento"]), [9])

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_classifies_past_today_and_future_days(self, _mock_localdate):
        paciente = self.create_paciente()
        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        days = {day.day: day.temporal_state for day in table.days}

        self.assertEqual(days[5], DAY_PAST)
        self.assertEqual(days[6], DAY_TODAY)
        self.assertEqual(days[7], DAY_FUTURE)

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_uses_fixed_number_of_queries(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        categoria = self.create_categoria(nome="Reformer")
        session = self.create_completed_session(procedimento, datetime(2026, 5, 1, 9, 0))

        for index in range(12):
            exercise = self.create_exercicio(nome=f"Exercicio query {index}", categoria=categoria)
            ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercise)
            SessaoExercicio.objects.create(sessao=session, exercicio=exercise)

        with CaptureQueriesContext(connection) as captured:
            table = build_monthly_exercise_tracking_table(paciente, date(2026, 5, 1))

        exercise_count = sum(len(group.exercises) for group in table.groups)
        self.assertEqual(exercise_count, 12)
        self.assertLessEqual(len(captured), 8)

    @patch("forms.exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_patient_detail_injects_presented_monthly_tracking_for_requested_month(self, _mock_localdate):
        user = self.create_user()
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Controle no detalhe")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)
        session = self.create_completed_session(procedimento, datetime(2026, 4, 10, 9, 0))
        SessaoExercicio.objects.create(sessao=session, exercicio=exercicio)
        self.client.force_login(user)

        response = self.client.get(reverse("inscricao-detail", args=[paciente.pk]), {"month": "2026-04"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["exercise_tracking"]["month_param"], "2026-04")
        self.assertContains(response, "Controle Mensal de Exercícios")
        self.assertContains(response, "Controle no detalhe")
        self.assertContains(response, "X")

    def create_completed_session(self, procedimento, when):
        return self.create_session_with_status(procedimento, when, Sessao.STATUS_REALIZADA)

    def create_session_with_status(self, procedimento, when, status):
        return Sessao.objects.create(
            procedimento=procedimento,
            data_hora=timezone.make_aware(when),
            duracao_minutos=60,
            status=status,
        )

    def exercise_rows_by_name(self, table):
        return {
            exercise.name: exercise
            for group in table.groups
            for exercise in group.exercises
        }

    def performed_days(self, row):
        return [day.day for day in row.days if day.performed]
