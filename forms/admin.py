from django.contrib import admin

from .models import Avaliacao, FichaExercicios, Paciente, Procedimento, Sessao, TipoAvaliacao, TipoProcedimento


class SoftDeleteAdminMixin:
    """Admin que exibe status e converte deleções em soft delete."""

    actions = ("soft_delete_selected",)

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()

    @admin.action(description="Desativar selecionados")
    def soft_delete_selected(self, request, queryset):
        queryset.delete()

    def delete_model(self, request, obj):
        obj.delete()

    def delete_queryset(self, request, queryset):
        queryset.delete()

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Paciente)
class PacienteAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "cpf", "email", "data_matricula", "is_active", "created_at")
    search_fields = ("nome", "cpf", "email")
    list_filter = ("is_active", "data_matricula", "created_at")


@admin.register(TipoAvaliacao)
class TipoAvaliacaoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "is_active")
    search_fields = ("nome",)
    list_filter = ("is_active",)


@admin.register(Avaliacao)
class AvaliacaoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("paciente", "tipo_avaliacao", "data_hora", "concluida", "is_active")
    list_filter = ("is_active", "tipo_avaliacao", "concluida")
    search_fields = ("paciente__nome", "tipo_avaliacao__nome")


@admin.register(TipoProcedimento)
class TipoProcedimentoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "is_active")
    search_fields = ("nome",)
    list_filter = ("is_active",)


class SessaoInline(admin.TabularInline):
    model = Sessao
    extra = 0

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()


@admin.register(Procedimento)
class ProcedimentoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("paciente", "tipo_procedimento", "concluido", "is_active", "created_at")
    list_filter = ("is_active", "tipo_procedimento", "concluido", "created_at")
    search_fields = ("paciente__nome", "tipo_procedimento__nome")
    inlines = [SessaoInline]


@admin.register(Sessao)
class SessaoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("procedimento", "data_hora", "numero", "status", "assinatura_confirmada", "is_active")
    list_filter = ("is_active", "status", "assinatura_confirmada", "data_hora")
    search_fields = ("procedimento__paciente__nome", "procedimento__tipo_procedimento__nome", "observacoes")


@admin.register(FichaExercicios)
class FichaExerciciosAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "paciente", "procedimento", "ativo", "is_active", "created_at")
    list_filter = ("is_active", "ativo", "created_at")
    search_fields = ("titulo", "paciente__nome", "observacoes")
