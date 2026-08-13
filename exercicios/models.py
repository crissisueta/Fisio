from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from core.models import SoftDeleteModel, TimestampedModel
from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao


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
        db_table = "forms_fichaexercicios"
        verbose_name = "Ficha de Exercícios"
        verbose_name_plural = "Fichas de Exercícios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titulo} - {self.paciente.nome}"


class CategoriaExercicio(SoftDeleteModel, models.Model):
    """Categorias administrativas para organizar exercícios."""

    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)
    cor = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Informe uma cor hexadecimal no formato #RRGGBB.",
            )
        ],
    )

    class Meta:
        db_table = "forms_categoriaexercicio"
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

    nome = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        CategoriaExercicio,
        on_delete=models.PROTECT,
        related_name="exercicios",
    )
    descricao = models.TextField(blank=True)
    instrucoes = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    max_sessoes_consecutivas = models.PositiveIntegerField(default=2)
    sessoes_ate_cooldown = models.PositiveIntegerField(default=2)

    class Meta:
        db_table = "forms_exerciciocatalogo"
        verbose_name = "Exercício"
        verbose_name_plural = "Exercícios"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                "categoria",
                condition=models.Q(is_active=True),
                name="unique_active_exercicio_por_categoria_nome",
            )
        ]

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

    class Status(models.TextChoices):
        PLANEJADO = "planejado", "Planejado"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDO = "concluido", "Concluído"

    STATUS_PLANEJADO = Status.PLANEJADO
    STATUS_EM_ANDAMENTO = Status.EM_ANDAMENTO
    STATUS_CONCLUIDO = Status.CONCLUIDO
    STATUS_CHOICES = Status.choices

    procedimento = models.ForeignKey(Procedimento, on_delete=models.CASCADE, related_name="procedimento_exercicios")
    exercicio = models.ForeignKey(ExercicioCatalogo, on_delete=models.PROTECT, related_name="procedimento_exercicios")
    ordem = models.PositiveIntegerField(default=0)
    series = models.CharField(max_length=50, blank=True)
    repeticoes = models.CharField(max_length=50, blank=True)
    frequencia = models.CharField(max_length=100, blank=True)
    progressao = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANEJADO)

    class Meta:
        db_table = "forms_procedimentoexercicio"
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


class SessaoExercicio(SoftDeleteModel, TimestampedModel):
    """Vínculo entre sessão específica e exercício selecionado."""

    ACTIVE_RELATED_FILTERS = {
        "sessao__is_active": True,
        "sessao__procedimento__is_active": True,
        "sessao__procedimento__paciente__is_active": True,
        "sessao__procedimento__tipo_procedimento__is_active": True,
        "exercicio__is_active": True,
        "exercicio__categoria__is_active": True,
    }

    STATUS_PLANEJADO = ProcedimentoExercicio.STATUS_PLANEJADO
    STATUS_EM_ANDAMENTO = ProcedimentoExercicio.STATUS_EM_ANDAMENTO
    STATUS_CONCLUIDO = ProcedimentoExercicio.STATUS_CONCLUIDO
    STATUS_CHOICES = ProcedimentoExercicio.STATUS_CHOICES

    sessao = models.ForeignKey(Sessao, on_delete=models.CASCADE, related_name="sessao_exercicios")
    exercicio = models.ForeignKey(ExercicioCatalogo, on_delete=models.PROTECT, related_name="sessao_exercicios")
    ordem = models.PositiveIntegerField(default=0)
    series = models.CharField(max_length=50, blank=True)
    repeticoes = models.CharField(max_length=50, blank=True)
    frequencia = models.CharField(max_length=100, blank=True)
    progressao = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANEJADO)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "forms_sessaoexercicio"
        verbose_name = "Exercício da Sessão"
        verbose_name_plural = "Exercícios da Sessão"
        ordering = ["ordem", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sessao", "exercicio"],
                condition=models.Q(is_active=True),
                name="unique_active_exercicio_por_sessao",
            )
        ]

    def __str__(self):
        return f"{self.sessao} - {self.exercicio}"
