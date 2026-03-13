from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """Modelo base abstrato com timestamps automáticos."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet com suporte a soft delete em lote."""

    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def delete(self):
        return self.soft_delete()

    def soft_delete(self):
        timestamp = timezone.now()
        updated = self.filter(is_active=True).update(is_active=False, deleted_at=timestamp)
        return updated, {self.model._meta.label: updated}

    def hard_delete(self):
        return super().delete()


class ActiveManager(models.Manager):
    """Manager padrão que expõe somente registros ativos."""

    def get_queryset(self):
        queryset = SoftDeleteQuerySet(self.model, using=self._db).active()
        related_filters = getattr(self.model, "ACTIVE_RELATED_FILTERS", {})
        if related_filters:
            queryset = queryset.filter(**related_filters)
        return queryset


class AllObjectsManager(models.Manager):
    """Manager para acesso administrativo/debug a todos os registros."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """Modelo base abstrato com desativação lógica."""

    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"
        default_manager_name = "objects"

    def delete(self, using=None, keep_parents=False):
        if not self.is_active:
            return 0, {}

        self.is_active = False
        self.deleted_at = timezone.now()
        update_fields = ["is_active", "deleted_at"]

        if hasattr(self, "updated_at"):
            self.updated_at = self.deleted_at
            update_fields.append("updated_at")

        self.save(update_fields=update_fields)
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_active = True
        self.deleted_at = None
        update_fields = ["is_active", "deleted_at"]

        if hasattr(self, "updated_at"):
            self.updated_at = timezone.now()
            update_fields.append("updated_at")

        self.save(update_fields=update_fields)


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


class TipoAvaliacao(SoftDeleteModel, models.Model):
    """Tipos de avaliação clínica."""
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
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
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.tipo_avaliacao} - {self.paciente}"


class TipoProcedimento(SoftDeleteModel, models.Model):
    """Tipos de procedimento terapêutico."""
    nome = models.CharField(max_length=100, unique=True)
    habilita_exercicios = models.BooleanField(default=False)

    class Meta:
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


class FichaExercicios(SoftDeleteModel, TimestampedModel):
    """Estrutura base para ficha de exercícios (evolução futura)."""
    ACTIVE_RELATED_FILTERS = {
        "paciente__is_active": True,
    }

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


class CategoriaExercicio(SoftDeleteModel, models.Model):
    """Categorias administrativas para organizar exercícios."""

    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoria de Exercício"
        verbose_name_plural = "Categorias de Exercícios"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ExercicioCatalogo(SoftDeleteModel, TimestampedModel):
    """Catálogo administrativo de exercícios disponíveis para procedimentos."""
    ACTIVE_RELATED_FILTERS = {
        "categoria__is_active": True,
    }

    nome = models.CharField(max_length=150, unique=True)
    categoria = models.ForeignKey(
        CategoriaExercicio,
        on_delete=models.PROTECT,
        related_name="exercicios",
    )
    descricao = models.TextField(blank=True)
    instrucoes = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Exercício"
        verbose_name_plural = "Exercícios"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ProcedimentoExercicio(SoftDeleteModel, TimestampedModel):
    """Vínculo entre procedimento do paciente e exercício selecionado."""
    ACTIVE_RELATED_FILTERS = {
        "procedimento__is_active": True,
        "procedimento__paciente__is_active": True,
        "procedimento__tipo_procedimento__is_active": True,
        "exercicio__is_active": True,
        "exercicio__categoria__is_active": True,
    }

    STATUS_PLANEJADO = "planejado"
    STATUS_EM_ANDAMENTO = "em_andamento"
    STATUS_CONCLUIDO = "concluido"
    STATUS_CHOICES = [
        (STATUS_PLANEJADO, "Planejado"),
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_CONCLUIDO, "Concluído"),
    ]

    procedimento = models.ForeignKey(Procedimento, on_delete=models.CASCADE, related_name="procedimento_exercicios")
    exercicio = models.ForeignKey(ExercicioCatalogo, on_delete=models.PROTECT, related_name="procedimento_exercicios")
    ordem = models.PositiveIntegerField(default=0)
    series = models.CharField(max_length=50, blank=True)
    repeticoes = models.CharField(max_length=50, blank=True)
    frequencia = models.CharField(max_length=100, blank=True)
    progressao = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANEJADO)

    class Meta:
        verbose_name = "Exercício do Procedimento"
        verbose_name_plural = "Exercícios do Procedimento"
        ordering = ["ordem", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["procedimento", "exercicio"],
                condition=models.Q(is_active=True),
                name="unique_active_exercicio_por_procedimento",
            )
        ]

    def __str__(self):
        return f"{self.procedimento} - {self.exercicio}"
