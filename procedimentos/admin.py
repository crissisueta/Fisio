from django.contrib import admin

from core.admin import SoftDeleteAdminMixin
from exercicios.models import ProcedimentoExercicio, SessaoExercicio
from .models import Procedimento, Sessao, TipoProcedimento


@admin.register(TipoProcedimento)
class TipoProcedimentoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "habilita_exercicios", "is_active")
    search_fields = ("nome",)
    list_filter = ("is_active", "habilita_exercicios")


class SessaoInline(admin.TabularInline):
    model = Sessao
    extra = 0

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()


class ProcedimentoExercicioInline(admin.TabularInline):
    model = ProcedimentoExercicio
    extra = 0
    autocomplete_fields = ("exercicio",)
    fields = ("exercicio", "ordem", "series", "repeticoes", "frequencia", "status", "observacoes", "is_active")

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related("exercicio")


class SessaoExercicioInline(admin.TabularInline):
    model = SessaoExercicio
    extra = 0
    autocomplete_fields = ("exercicio",)
    fields = ("exercicio", "ordem", "series", "repeticoes", "frequencia", "status", "observacoes", "is_active")

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related("exercicio")


@admin.register(Procedimento)
class ProcedimentoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("paciente", "tipo_procedimento", "concluido", "is_active", "created_at")
    list_filter = ("is_active", "tipo_procedimento", "concluido", "created_at")
    search_fields = ("paciente__nome", "tipo_procedimento__nome")
    inlines = [SessaoInline, ProcedimentoExercicioInline]


@admin.register(Sessao)
class SessaoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("procedimento", "data_hora", "numero", "status", "assinatura_confirmada", "is_active")
    list_filter = ("is_active", "status", "assinatura_confirmada", "data_hora")
    search_fields = ("procedimento__paciente__nome", "procedimento__tipo_procedimento__nome", "observacoes")
    inlines = [SessaoExercicioInline]

