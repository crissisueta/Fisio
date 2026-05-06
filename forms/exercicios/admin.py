from django.contrib import admin

from ..core.admin import SoftDeleteAdminMixin
from .models import (
    CategoriaExercicio,
    ExercicioCatalogo,
    FichaExercicios,
    ProcedimentoExercicio,
    SessaoExercicio,
)


@admin.register(FichaExercicios)
class FichaExerciciosAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "paciente", "procedimento", "ativo", "is_active", "created_at")
    list_filter = ("is_active", "ativo", "created_at")
    search_fields = ("titulo", "paciente__nome", "observacoes")


@admin.register(CategoriaExercicio)
class CategoriaExercicioAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "is_active")
    list_filter = ("is_active",)
    search_fields = ("nome", "descricao")


@admin.register(ExercicioCatalogo)
class ExercicioCatalogoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "nome",
        "categoria",
        "max_sessoes_consecutivas",
        "sessoes_ate_cooldown",
        "ativo",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "ativo", "categoria", "created_at")
    search_fields = ("nome", "categoria__nome", "descricao", "instrucoes", "observacoes")
    autocomplete_fields = ("categoria",)


@admin.register(ProcedimentoExercicio)
class ProcedimentoExercicioAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("procedimento", "exercicio", "status", "ordem", "is_active", "created_at")
    list_filter = ("is_active", "status", "created_at")
    search_fields = (
        "procedimento__paciente__nome",
        "procedimento__tipo_procedimento__nome",
        "exercicio__nome",
        "observacoes",
    )
    autocomplete_fields = ("procedimento", "exercicio")


@admin.register(SessaoExercicio)
class SessaoExercicioAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("sessao", "exercicio", "status", "ordem", "is_active", "created_at")
    list_filter = ("is_active", "status", "created_at")
    search_fields = (
        "sessao__procedimento__paciente__nome",
        "sessao__procedimento__tipo_procedimento__nome",
        "exercicio__nome",
        "observacoes",
    )
    autocomplete_fields = ("sessao", "exercicio")

