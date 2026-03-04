from django.contrib import admin
from .models import (
    FichaInscricao, AnamneseGeral, AnamneseAcupuntura,
    FichaDrenagem, FichaExercicios
)


@admin.register(FichaInscricao)
class FichaInscricaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'email', 'data_matricula', 'criado_em')
    list_filter = ('data_matricula', 'criado_em')
    search_fields = ('nome', 'cpf', 'email')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(AnamneseGeral)
class AnamneseGeralAdmin(admin.ModelAdmin):
    list_display = ('nome', 'profissao', 'data_nascimento', 'data', 'criado_em')
    list_filter = ('data', 'criado_em', 'diabetes', 'anemia', 'pressao_alta')
    search_fields = ('nome', 'profissao')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(AnamneseAcupuntura)
class AnamneseAcupunturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_consulta', 'profissao', 'idade', 'criado_em')
    list_filter = ('data_consulta', 'criado_em', 'ja_fez_acupuntura')
    search_fields = ('nome', 'profissao')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(FichaDrenagem)
class FichaDrenagemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'idade', 'altura', 'peso', 'criado_em')
    list_filter = ('data', 'criado_em')
    search_fields = ('nome', 'convenio')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(FichaExercicios)
class FichaExerciciosAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'dia', 'criado_em')
    list_filter = ('dia', 'criado_em')
    search_fields = ('aluno', 'objetivo')
    readonly_fields = ('criado_em', 'atualizado_em')
