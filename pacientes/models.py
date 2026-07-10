from django.db import models

from core.models import SoftDeleteModel, TimestampedModel


class Paciente(SoftDeleteModel, TimestampedModel):
    """Cadastro de paciente."""

    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True)

    profissao = models.CharField(max_length=100, blank=True)

    endereco = models.CharField(max_length=300, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cep = models.CharField(max_length=10, blank=True)

    telefone = models.CharField(max_length=15, blank=True)
    celular = models.CharField(max_length=15, blank=True)
    telefone_comercial = models.CharField(max_length=15, blank=True)

    data_nascimento = models.DateField(blank=True, null=True)
    data_matricula = models.DateField(blank=True, null=True)

    plano = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)
    nota_exercicios = models.CharField(max_length=200, blank=True)

    REQUIRED_PROFILE_FIELDS = [
        "cpf",
        "email",
        "endereco",
        "bairro",
        "cep",
        "celular",
        "data_nascimento",
        "data_matricula",
        "plano",
    ]
    REQUIRED_PROFILE_FIELD_LABELS = {
        "cpf": "CPF",
        "email": "Email",
        "endereco": "Endereco",
        "bairro": "Bairro",
        "cep": "CEP",
        "celular": "Celular",
        "data_nascimento": "Data de Nascimento",
        "data_matricula": "Data de Matricula",
        "plano": "Plano",
    }

    class Meta:
        db_table = "forms_paciente"
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["-created_at"]

    def __str__(self):
        identifier = self.cpf or "cadastro incompleto"
        return f"{self.nome} - {identifier}"

    @property
    def profile_missing_fields(self):
        return [
            field_name
            for field_name in self.REQUIRED_PROFILE_FIELDS
            if not getattr(self, field_name)
        ]

    @property
    def profile_incomplete(self):
        return bool(self.profile_missing_fields)

    @property
    def profile_missing_field_labels(self):
        return [
            self.REQUIRED_PROFILE_FIELD_LABELS.get(
                field_name,
                self._meta.get_field(field_name).verbose_name.title(),
            )
            for field_name in self.profile_missing_fields
        ]
