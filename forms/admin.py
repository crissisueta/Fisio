from django.contrib import admin

from .models import Avaliacao, FichaExercicios, Paciente, Procedimento, Sessao, TipoAvaliacao, TipoProcedimento


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "email", "data_matricula", "created_at")
    search_fields = ("nome", "cpf", "email")
    list_filter = ("data_matricula", "created_at")


@admin.register(TipoAvaliacao)
class TipoAvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("paciente", "tipo_avaliacao", "data_hora", "concluida")
    list_filter = ("tipo_avaliacao", "concluida")
    search_fields = ("paciente__nome", "tipo_avaliacao__nome")


@admin.register(TipoProcedimento)
class TipoProcedimentoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


class SessaoInline(admin.TabularInline):
    model = Sessao
    extra = 0


@admin.register(Procedimento)
class ProcedimentoAdmin(admin.ModelAdmin):
    list_display = ("paciente", "tipo_procedimento", "concluido", "created_at")
    list_filter = ("tipo_procedimento", "concluido", "created_at")
    search_fields = ("paciente__nome", "tipo_procedimento__nome")
    inlines = [SessaoInline]


@admin.register(Sessao)
class SessaoAdmin(admin.ModelAdmin):
    list_display = ("procedimento", "data_hora", "numero", "status", "assinatura_confirmada")
    list_filter = ("status", "assinatura_confirmada", "data_hora")
    search_fields = ("procedimento__paciente__nome", "procedimento__tipo_procedimento__nome", "observacoes")


@admin.register(FichaExercicios)
class FichaExerciciosAdmin(admin.ModelAdmin):
    list_display = ("titulo", "paciente", "procedimento", "ativo", "created_at")
    list_filter = ("ativo", "created_at")
    search_fields = ("titulo", "paciente__nome", "observacoes")
