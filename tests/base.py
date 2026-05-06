from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.utils import timezone

from forms.models import CategoriaExercicio, ExercicioCatalogo, Paciente, Procedimento, Sessao, TipoProcedimento
from forms.services.scheduling_service import create_session_for_procedimento


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

