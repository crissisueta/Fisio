from django.db import models


class TimestampedModel(models.Model):
    """Abstract base model that provides automatic timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FichaInscricao(TimestampedModel):
    """Patient registration"""
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
        verbose_name = "Ficha de Inscrição"
        verbose_name_plural = "Fichas de Inscrição"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nome} - {self.cpf}"


class ProcedureType(models.Model):
    """Type of treatment (Anamnese, Drenagem, etc)"""

    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Tipo de Procedimento"
        verbose_name_plural = "Tipos de Procedimento"

    def __str__(self):
        return self.name


class Procedure(TimestampedModel):
    """A treatment plan for a patient"""

    patient = models.ForeignKey(
        FichaInscricao,
        on_delete=models.CASCADE,
        related_name="procedures"
    )

    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE
    )

    observacoes = models.TextField(blank=True)

    is_complete = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Procedimento"
        verbose_name_plural = "Procedimentos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.procedure_type} - {self.patient}"


class ProcedureSession(TimestampedModel):
    """Individual appointment/session of a procedure"""
    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_MISSED = "missed"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Agendada"),
        (STATUS_COMPLETED, "Concluída"),
        (STATUS_CANCELLED, "Cancelada"),
        (STATUS_MISSED, "Faltou"),
    ]

    procedure = models.ForeignKey(
        Procedure,
        related_name="sessions",
        on_delete=models.CASCADE
    )

    scheduled_datetime = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)

    notes = models.TextField(blank=True)

    completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"
        ordering = ["scheduled_datetime"]

    def save(self, *args, **kwargs):
        # Keep backward compatibility with the previous boolean completion flag.
        if self.status == self.STATUS_COMPLETED:
            self.completed = True
        elif self.completed and self.status == self.STATUS_SCHEDULED:
            self.status = self.STATUS_COMPLETED
        else:
            self.completed = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.procedure} - {self.scheduled_datetime}"
