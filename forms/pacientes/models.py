from django.db import models

from ..core.models import SoftDeleteModel, TimestampedModel


class Paciente(SoftDeleteModel, TimestampedModel):
    """Cadastro de paciente."""

    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField()

    profissao = models.CharField(max_length=100, blank=True)

    endereco = models.CharField(max_length=300)
    bairro = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)

    telefone = models.CharField(max_length=15, blank=True)
    celular = models.CharField(max_length=15)
    telefone_comercial = models.CharField(max_length=15, blank=True)

    data_nascimento = models.DateField()
    data_matricula = models.DateField()

    plano = models.CharField(max_length=100)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nome} - {self.cpf}"

