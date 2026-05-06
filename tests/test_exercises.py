from django.urls import reverse

from forms.models import ProcedimentoExercicio, SessaoExercicio

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

