import json
from datetime import date, datetime
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from exercicios.services.monthly_tracking import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_RED,
    DAY_FUTURE,
    DAY_PAST,
    DAY_TODAY,
    build_monthly_exercise_tracking_table,
    mark_exercise_day_for_patient,
    unmark_exercise_day_for_patient,
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

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
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

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
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

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
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

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_classifies_past_today_and_future_days(self, _mock_localdate):
        paciente = self.create_paciente()
        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        days = {day.day: day.temporal_state for day in table.days}

        self.assertEqual(days[5], DAY_PAST)
        self.assertEqual(days[6], DAY_TODAY)
        self.assertEqual(days[7], DAY_FUTURE)

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
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

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_monthly_tracking_uses_procedure_exercise_order(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        estabilizadores = self.create_categoria(nome="Estabilizadores")
        barril = self.create_categoria(nome="Barril")
        cadeira = self.create_categoria(nome="Cadeira")
        bosu = self.create_exercicio(nome="Bosu", categoria=estabilizadores)
        bola = self.create_exercicio(nome="Bola", categoria=estabilizadores)
        cavalo = self.create_exercicio(nome="A cavalo", categoria=barril)
        apoio = self.create_exercicio(nome="Apoio em pé", categoria=cadeira)

        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=bosu, ordem=1)
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=bola, ordem=2)
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=cavalo, ordem=3)
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=apoio, ordem=4)

        table = build_monthly_exercise_tracking_table(paciente, "2026-05")

        self.assertEqual([group.category_name for group in table.groups], ["Estabilizadores", "Barril", "Cadeira"])
        self.assertEqual([exercise.name for exercise in table.groups[0].exercises], ["Bosu", "Bola"])

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_mark_exercise_day_creates_completed_session_and_marks_table(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Marcado pelo controle mensal")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)

        result = mark_exercise_day_for_patient(
            paciente,
            exercise_id=exercicio.pk,
            target_date=date(2026, 5, 3),
        )

        self.assertTrue(result.created_session)
        self.assertTrue(result.created_link)
        self.assertEqual(result.sessao.procedimento, procedimento)
        self.assertEqual(timezone.localtime(result.sessao.data_hora).date(), date(2026, 5, 3))
        self.assertEqual(result.sessao.status, Sessao.STATUS_REALIZADA)
        self.assertEqual(result.sessao_exercicio.status, SessaoExercicio.STATUS_CONCLUIDO)

        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        row = self.exercise_rows_by_name(table)["Marcado pelo controle mensal"]
        self.assertEqual(self.performed_days(row), [3])
        self.assertEqual(row.color_state, COLOR_RED)

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_mark_exercise_day_creates_scheduled_session_for_future_day(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Agendado pelo controle mensal")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)

        result = mark_exercise_day_for_patient(
            paciente,
            exercise_id=exercicio.pk,
            target_date=date(2026, 5, 12),
        )

        self.assertEqual(result.sessao.status, Sessao.STATUS_AGENDADA)
        self.assertEqual(result.sessao_exercicio.status, SessaoExercicio.STATUS_PLANEJADO)

        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        row = self.exercise_rows_by_name(table)["Agendado pelo controle mensal"]
        self.assertEqual(self.performed_days(row), [12])
        self.assertEqual(row.color_state, COLOR_BLACK)

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_unmark_exercise_day_removes_table_created_mark(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Desmarcado pelo controle mensal")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)
        mark_result = mark_exercise_day_for_patient(
            paciente,
            exercise_id=exercicio.pk,
            target_date=date(2026, 5, 3),
        )

        result = unmark_exercise_day_for_patient(
            paciente,
            exercise_id=exercicio.pk,
            target_date=date(2026, 5, 3),
        )

        self.assertTrue(result.deleted_session)
        self.assertFalse(Sessao.objects.filter(pk=mark_result.sessao.pk).exists())
        self.assertFalse(SessaoExercicio.objects.filter(pk=mark_result.sessao_exercicio.pk).exists())
        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        row = self.exercise_rows_by_name(table)["Desmarcado pelo controle mensal"]
        self.assertEqual(self.performed_days(row), [])

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_unmark_fallback_session_materializes_remaining_exercises(self, _mock_localdate):
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        removed_exercise = self.create_exercicio(nome="Remover do fallback")
        remaining_exercise = self.create_exercicio(nome="Manter no fallback")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=removed_exercise)
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=remaining_exercise)
        self.create_session_with_status(procedimento, datetime(2026, 5, 5, 9, 0), Sessao.STATUS_REALIZADA)

        result = unmark_exercise_day_for_patient(
            paciente,
            exercise_id=removed_exercise.pk,
            target_date=date(2026, 5, 5),
        )

        self.assertFalse(result.deleted_session)
        table = build_monthly_exercise_tracking_table(paciente, "2026-05")
        rows = self.exercise_rows_by_name(table)
        self.assertEqual(self.performed_days(rows["Remover do fallback"]), [])
        self.assertEqual(self.performed_days(rows["Manter no fallback"]), [5])

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_patient_exercise_day_mark_endpoint_is_patient_scoped(self, _mock_localdate):
        user = self.create_user()
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Marcado via endpoint")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)
        self.client.force_login(user)

        response = self.client.post(
            reverse("patient-exercise-day-mark", args=[paciente.pk]),
            data=json.dumps({"exercise_id": exercicio.pk, "date": "2026-05-04"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["exercise_id"], exercicio.pk)
        self.assertEqual(payload["date"], "2026-05-04")
        self.assertTrue(
            SessaoExercicio.objects.filter(
                sessao__procedimento=procedimento,
                exercicio=exercicio,
                sessao__status=Sessao.STATUS_REALIZADA,
            ).exists()
        )

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
    def test_patient_exercise_day_endpoint_unmarks_existing_mark(self, _mock_localdate):
        user = self.create_user()
        paciente = self.create_paciente()
        procedimento = self.create_procedimento(paciente=paciente)
        exercicio = self.create_exercicio(nome="Desmarcado via endpoint")
        ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)
        mark_exercise_day_for_patient(
            paciente,
            exercise_id=exercicio.pk,
            target_date=date(2026, 5, 4),
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("patient-exercise-day-mark", args=[paciente.pk]),
            data=json.dumps({"action": "unmark", "exercise_id": exercicio.pk, "date": "2026-05-04"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["action"], "unmark")
        self.assertEqual(payload["exercise_id"], exercicio.pk)
        self.assertFalse(
            SessaoExercicio.objects.filter(
                sessao__procedimento=procedimento,
                exercicio=exercicio,
            ).exists()
        )

    @patch("exercicios.services.monthly_tracking.timezone.localdate", return_value=date(2026, 5, 6))
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

    def test_patient_exercise_note_can_be_saved_beside_patient_name(self):
        user = self.create_user()
        paciente = self.create_paciente()
        self.client.force_login(user)

        response = self.client.post(
            reverse("patient-exercise-note-update", args=[paciente.pk]),
            {
                "nota_exercicios": "Evitar impacto no joelho",
                "month": "2026-05",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('inscricao-detail', args=[paciente.pk])}?month=2026-05",
            fetch_redirect_response=False,
        )
        paciente.refresh_from_db()
        self.assertEqual(paciente.nota_exercicios, "Evitar impacto no joelho")

        detail_response = self.client.get(reverse("inscricao-detail", args=[paciente.pk]))
        self.assertContains(detail_response, 'placeholder="Nota rápida"')
        self.assertContains(detail_response, 'value="Evitar impacto no joelho"')
        self.assertContains(detail_response, "data-exercise-note-input")
        self.assertNotContains(detail_response, ">Salvar</button>")

    def test_patient_exercise_note_ajax_save_returns_json(self):
        user = self.create_user()
        paciente = self.create_paciente()
        self.client.force_login(user)

        response = self.client.post(
            reverse("patient-exercise-note-update", args=[paciente.pk]),
            {"nota_exercicios": "Alongar antes"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"success": True, "nota_exercicios": "Alongar antes"},
        )
        paciente.refresh_from_db()
        self.assertEqual(paciente.nota_exercicios, "Alongar antes")

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
