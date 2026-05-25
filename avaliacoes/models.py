from django.db import models

from core.models import SoftDeleteModel, TimestampedModel
from pacientes.models import Paciente


class TipoAvaliacao(SoftDeleteModel, models.Model):
    """Tipos de avaliação clínica."""

    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "forms_tipoavaliacao"
        verbose_name = "Tipo de Avaliação"
        verbose_name_plural = "Tipos de Avaliação"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Avaliacao(SoftDeleteModel, TimestampedModel):
    """Avaliações não recorrentes do paciente."""

    ACTIVE_RELATED_FILTERS = {
        "paciente__is_active": True,
        "tipo_avaliacao__is_active": True,
    }

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="avaliacoes")
    tipo_avaliacao = models.ForeignKey(TipoAvaliacao, on_delete=models.PROTECT, related_name="avaliacoes")
    data_hora = models.DateTimeField()
    concluida = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        db_table = "forms_avaliacao"
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.tipo_avaliacao} - {self.paciente}"
