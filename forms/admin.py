from django.contrib import admin

from .models import FichaInscricao, Procedure, ProcedureSession, ProcedureType


@admin.register(FichaInscricao)
class FichaInscricaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "email", "data_matricula", "created_at")
    search_fields = ("nome", "cpf", "email")
    list_filter = ("data_matricula", "created_at")


@admin.register(ProcedureType)
class ProcedureTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class ProcedureSessionInline(admin.TabularInline):
    model = ProcedureSession
    extra = 0


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ("patient", "procedure_type", "is_complete", "created_at")
    list_filter = ("procedure_type", "is_complete", "created_at")
    search_fields = ("patient__nome", "procedure_type__name")
    inlines = [ProcedureSessionInline]


@admin.register(ProcedureSession)
class ProcedureSessionAdmin(admin.ModelAdmin):
    list_display = ("procedure", "scheduled_datetime", "status", "completed", "created_at")
    list_filter = ("status", "completed", "scheduled_datetime")
    search_fields = ("procedure__patient__nome", "procedure__procedure_type__name", "notes")
