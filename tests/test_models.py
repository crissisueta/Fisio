from django.urls import reverse

from forms.models import Paciente, ProcedimentoExercicio, SessaoExercicio

from .base import RegressionBaseTestCase


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

