from datetime import timedelta

from django.db import models

from core.models import SoftDeleteModel, TimestampedModel
from pacientes.models import Paciente


class TipoProcedimento(SoftDeleteModel, models.Model):
    """Tipos de procedimento terapêutico."""

    nome = models.CharField(max_length=100, unique=True)
    habilita_exercicios = models.BooleanField(default=False)

    class Meta:
        db_table = "forms_tipoprocedimento"
        verbose_name = "Tipo de Procedimento"
        verbose_name_plural = "Tipos de Procedimento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Procedimento(SoftDeleteModel, TimestampedModel):
    """Plano de tratamento de um paciente."""

    ACTIVE_RELATED_FILTERS = {
        "paciente__is_active": True,
        "tipo_procedimento__is_active": True,
    }

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="procedimentos")
    tipo_procedimento = models.ForeignKey(TipoProcedimento, on_delete=models.PROTECT, related_name="procedimentos")
    observacoes = models.TextField(blank=True)
    concluido = models.BooleanField(default=False)

    class Meta:
        db_table = "forms_procedimento"
        verbose_name = "Procedimento"
        verbose_name_plural = "Procedimentos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo_procedimento} - {self.paciente}"


class Sessao(SoftDeleteModel, TimestampedModel):
    """Sessão/atendimento vinculado a um procedimento."""

    ACTIVE_RELATED_FILTERS = {
        "procedimento__is_active": True,
        "procedimento__paciente__is_active": True,
        "procedimento__tipo_procedimento__is_active": True,
    }

    class Status(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        REALIZADA = "realizada", "Realizada"
        FALTOU = "faltou", "Faltou"
        CANCELADA = "cancelada", "Cancelada"

    STATUS_AGENDADA = Status.AGENDADA
    STATUS_REALIZADA = Status.REALIZADA
    STATUS_FALTOU = Status.FALTOU
    STATUS_CANCELADA = Status.CANCELADA
    STATUS_CHOICES = Status.choices

    procedimento = models.ForeignKey(Procedimento, related_name="sessoes", on_delete=models.CASCADE)
    data_hora = models.DateTimeField()
    duracao_minutos = models.PositiveIntegerField(default=60)
    numero = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AGENDADA)
    assinatura_confirmada = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        db_table = "forms_sessao"
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"
        ordering = ["data_hora"]

    def __str__(self):
        return f"{self.procedimento} - {self.data_hora}"

    @property
    def data_hora_fim(self):
        return self.data_hora + timedelta(minutes=self.duracao_minutos)
