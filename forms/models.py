from django.db import models


class TimestampedModel(models.Model):
    """Modelo base abstrato com timestamps automáticos."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Paciente(TimestampedModel):
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


class TipoAvaliacao(models.Model):
    """Tipos de avaliação clínica."""
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tipo de Avaliação"
        verbose_name_plural = "Tipos de Avaliação"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Avaliacao(TimestampedModel):
    """Avaliações não recorrentes do paciente."""
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="avaliacoes")
    tipo_avaliacao = models.ForeignKey(TipoAvaliacao, on_delete=models.PROTECT, related_name="avaliacoes")
    data_hora = models.DateTimeField()
    concluida = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.tipo_avaliacao} - {self.paciente}"


class TipoProcedimento(models.Model):
    """Tipos de procedimento terapêutico."""
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tipo de Procedimento"
        verbose_name_plural = "Tipos de Procedimento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Procedimento(TimestampedModel):
    """Plano de tratamento de um paciente."""
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="procedimentos")
    tipo_procedimento = models.ForeignKey(TipoProcedimento, on_delete=models.PROTECT, related_name="procedimentos")
    observacoes = models.TextField(blank=True)
    concluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Procedimento"
        verbose_name_plural = "Procedimentos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo_procedimento} - {self.paciente}"


class Sessao(TimestampedModel):
    """Sessão/atendimento vinculado a um procedimento."""

    STATUS_AGENDADA = "agendada"
    STATUS_REALIZADA = "realizada"
    STATUS_FALTOU = "faltou"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_AGENDADA, "Agendada"),
        (STATUS_REALIZADA, "Realizada"),
        (STATUS_FALTOU, "Faltou"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    procedimento = models.ForeignKey(Procedimento, related_name="sessoes", on_delete=models.CASCADE)
    data_hora = models.DateTimeField()
    numero = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AGENDADA)
    assinatura_confirmada = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"
        ordering = ["data_hora"]

    def __str__(self):
        return f"{self.procedimento} - {self.data_hora}"


class FichaExercicios(TimestampedModel):
    """Estrutura base para ficha de exercícios (evolução futura)."""
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="fichas_exercicios")
    procedimento = models.ForeignKey(
        Procedimento,
        on_delete=models.SET_NULL,
        related_name="fichas_exercicios",
        null=True,
        blank=True,
    )
    titulo = models.CharField(max_length=150)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ficha de Exercícios"
        verbose_name_plural = "Fichas de Exercícios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titulo} - {self.paciente.nome}"
