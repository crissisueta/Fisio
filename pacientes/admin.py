from django.contrib import admin

from core.admin import SoftDeleteAdminMixin
from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "cpf", "email", "data_matricula", "is_active", "created_at")
    search_fields = ("nome", "cpf", "email")
    list_filter = ("is_active", "data_matricula", "created_at")

