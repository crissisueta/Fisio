from django.contrib import admin
from .models import (
    FichaInscricao, AnamneseGeral, AnamneseAcupuntura,
    FichaDrenagem, FichaExercicios
)


@admin.register(FichaInscricao)
class FichaInscricaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'email', 'data_matricula', 'created_at')
    list_filter = ('data_matricula', 'created_at')
    search_fields = ('nome', 'cpf', 'email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AnamneseGeral)
class AnamneseGeralAdmin(admin.ModelAdmin):
    list_display = ('nome', 'profissao', 'data_nascimento', 'data', 'created_at')
    list_filter = ('data', 'created_at', 'diabetes', 'anemia', 'pressao_alta')
    search_fields = ('nome', 'profissao')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AnamneseAcupuntura)
class AnamneseAcupunturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_consulta', 'profissao', 'idade', 'created_at')
    list_filter = ('data_consulta', 'created_at', 'ja_fez_acupuntura')
    search_fields = ('nome', 'profissao')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FichaDrenagem)
class FichaDrenagemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'idade', 'altura', 'peso', 'created_at')
    list_filter = ('data', 'created_at')
    search_fields = ('nome', 'convenio')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FichaExercicios)
class FichaExerciciosAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'dia', 'created_at')
    list_filter = ('dia', 'created_at')
    search_fields = ('aluno', 'objetivo')
    readonly_fields = ('created_at', 'updated_at')
