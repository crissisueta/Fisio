from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError

from .models import Avaliacao, Paciente, Procedimento, Sessao
from .services.scheduling_service import WEEKDAY_CHOICES


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "nome",
            "cpf",
            "email",
            "profissao",
            "endereco",
            "bairro",
            "cep",
            "telefone",
            "celular",
            "telefone_comercial",
            "data_nascimento",
            "data_matricula",
            "plano",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
            "cpf": forms.TextInput(attrs={"class": "form-control", "placeholder": "000.000.000-00"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@exemplo.com"}),
            "profissao": forms.TextInput(attrs={"class": "form-control"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "bairro": forms.TextInput(attrs={"class": "form-control"}),
            "cep": forms.TextInput(attrs={"class": "form-control", "placeholder": "00000-000"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "celular": forms.TextInput(attrs={"class": "form-control"}),
            "telefone_comercial": forms.TextInput(attrs={"class": "form-control"}),
            "data_nascimento": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "data_matricula": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "plano": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        fields = ["paciente", "tipo_avaliacao", "data_hora", "concluida", "observacoes"]
        widgets = {
            "paciente": forms.Select(attrs={"class": "form-select"}),
            "tipo_avaliacao": forms.Select(attrs={"class": "form-select"}),
            "data_hora": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "concluida": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
        labels = {
            "paciente": "Paciente",
            "tipo_avaliacao": "Tipo de Avaliação",
            "data_hora": "Data e Hora",
            "concluida": "Concluída",
            "observacoes": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora"].input_formats = ["%Y-%m-%dT%H:%M"]


class ProcedimentoForm(forms.ModelForm):
    MODO_AGENDAMENTO_UNICO = "unico"
    MODO_AGENDAMENTO_LOTE = "lote"
    MODO_AGENDAMENTO_CHOICES = [
        (MODO_AGENDAMENTO_UNICO, "Agendar primeira sessão"),
        (MODO_AGENDAMENTO_LOTE, "Preencher período"),
    ]

    modo_agendamento = forms.ChoiceField(
        choices=MODO_AGENDAMENTO_CHOICES,
        initial=MODO_AGENDAMENTO_UNICO,
        widget=forms.RadioSelect,
        label="Como deseja agendar?",
    )
    data_sessao_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
        label="Data da primeira sessão",
    )
    hora_sessao_inicial = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
        label="Horário da primeira sessão",
    )

    class Meta:
        model = Procedimento
        fields = ["paciente", "tipo_procedimento", "observacoes", "concluido"]
        widgets = {
            "paciente": forms.Select(attrs={"class": "form-select"}),
            "tipo_procedimento": forms.Select(attrs={"class": "form-select"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "concluido": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "paciente": "Paciente",
            "tipo_procedimento": "Tipo de Procedimento",
            "observacoes": "Observações",
            "concluido": "Concluído",
        }

    def __init__(self, *args, **kwargs):
        self.enable_schedule_fields = kwargs.pop("enable_schedule_fields", True)
        super().__init__(*args, **kwargs)
        self.fields["data_sessao_inicial"].input_formats = ["%Y-%m-%d"]
        self.fields["hora_sessao_inicial"].input_formats = ["%H:%M"]

        if not self.enable_schedule_fields:
            for field_name in ("modo_agendamento", "data_sessao_inicial", "hora_sessao_inicial"):
                self.fields.pop(field_name, None)

    def clean(self):
        cleaned_data = super().clean()
        if not self.enable_schedule_fields:
            return cleaned_data

        modo_agendamento = cleaned_data.get("modo_agendamento")
        data_sessao_inicial = cleaned_data.get("data_sessao_inicial")
        hora_sessao_inicial = cleaned_data.get("hora_sessao_inicial")

        if modo_agendamento == self.MODO_AGENDAMENTO_UNICO:
            if not data_sessao_inicial:
                self.add_error("data_sessao_inicial", "Informe a data da primeira sessão.")
            if not hora_sessao_inicial:
                self.add_error("hora_sessao_inicial", "Informe o horário da primeira sessão.")

        return cleaned_data

    def get_initial_session_datetime(self):
        data_sessao = self.cleaned_data["data_sessao_inicial"]
        hora_sessao = self.cleaned_data["hora_sessao_inicial"]
        return datetime.combine(data_sessao, hora_sessao)


class SessaoForm(forms.ModelForm):
    class Meta:
        model = Sessao
        fields = ["data_hora", "status", "assinatura_confirmada", "observacoes"]
        widgets = {
            "data_hora": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "assinatura_confirmada": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "data_hora": "Data e Hora",
            "status": "Status",
            "assinatura_confirmada": "Assinatura Confirmada",
            "observacoes": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora"].input_formats = ["%Y-%m-%dT%H:%M"]


class ProcedimentoBulkScheduleForm(forms.Form):
    referencia_mes = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "month"}, format="%Y-%m"),
        input_formats=["%Y-%m"],
        label="Mês de referência",
    )
    dias_semana = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Dias da semana",
    )
    hora_inicial = forms.TimeField(
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
        input_formats=["%H:%M"],
        label="Horário inicial",
    )
    hora_final = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
        input_formats=["%H:%M"],
        label="Horário final",
        help_text="Opcional. Usado apenas para validação e conferência visual neste fluxo.",
    )

    def clean_dias_semana(self):
        values = self.cleaned_data["dias_semana"]
        if not values:
            raise ValidationError("Selecione ao menos um dia da semana.")
        return [int(value) for value in values]

    def clean(self):
        cleaned_data = super().clean()
        hora_inicial = cleaned_data.get("hora_inicial")
        hora_final = cleaned_data.get("hora_final")

        if hora_inicial and hora_final and hora_final <= hora_inicial:
            self.add_error("hora_final", "O horário final deve ser maior que o horário inicial.")

        return cleaned_data
