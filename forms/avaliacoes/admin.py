from django.contrib import admin

from ..core.admin import SoftDeleteAdminMixin
from .models import Avaliacao, TipoAvaliacao


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

