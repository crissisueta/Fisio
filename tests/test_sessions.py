from datetime import datetime

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from forms.models import Sessao
from forms.services.scheduling_service import create_session_for_procedimento, generate_sessions_for_month_by_weekday, update_sessao

from .base import RegressionBaseTestCase


class SessionLogicTests(RegressionBaseTestCase):
    def test_sessions_are_numbered_sequentially_in_chronological_order(self):
        procedimento = self.create_procedimento()

        terceira = self.create_sessao(procedimento, days_offset=3)
        primeira = self.create_sessao(procedimento, days_offset=1)
        segunda = self.create_sessao(procedimento, days_offset=2)

        terceira.refresh_from_db()
        primeira.refresh_from_db()
        segunda.refresh_from_db()

        numeros = list(procedimento.sessoes.order_by("data_hora").values_list("numero", flat=True))

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

