from django import forms
from django.core.exceptions import ValidationError

from core.utils.datetime import (
    combine_date_time,
    duration_minutes_for_datetime_end,
    duration_minutes_for_times,
)
from .models import Procedimento, Sessao, TipoProcedimento
from .services.scheduling import WEEKDAY_CHOICES


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
    hora_fim_sessao_inicial = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
        label="Horário final da primeira sessão",
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
        self.fields["hora_fim_sessao_inicial"].input_formats = ["%H:%M"]

        if not self.enable_schedule_fields:
            for field_name in (
                "modo_agendamento",
                "data_sessao_inicial",
                "hora_sessao_inicial",
                "hora_fim_sessao_inicial",
            ):
                self.fields.pop(field_name, None)

    def clean(self):
        cleaned_data = super().clean()
        if not self.enable_schedule_fields:
            return cleaned_data

        modo_agendamento = cleaned_data.get("modo_agendamento")
        data_sessao_inicial = cleaned_data.get("data_sessao_inicial")
        hora_sessao_inicial = cleaned_data.get("hora_sessao_inicial")
        hora_fim_sessao_inicial = cleaned_data.get("hora_fim_sessao_inicial")

        if modo_agendamento == self.MODO_AGENDAMENTO_UNICO:
            if not data_sessao_inicial:
                self.add_error("data_sessao_inicial", "Informe a data da primeira sessão.")
            if not hora_sessao_inicial:
                self.add_error("hora_sessao_inicial", "Informe o horário da primeira sessão.")
            if not hora_fim_sessao_inicial:
                self.add_error("hora_fim_sessao_inicial", "Informe o horário final da primeira sessão.")
            if hora_sessao_inicial and hora_fim_sessao_inicial and hora_fim_sessao_inicial <= hora_sessao_inicial:
                self.add_error("hora_fim_sessao_inicial", "O horário final deve ser maior que o horário inicial.")

        return cleaned_data

    def get_initial_session_datetime(self):
        return combine_date_time(
            self.cleaned_data["data_sessao_inicial"],
            self.cleaned_data["hora_sessao_inicial"],
        )

    def get_initial_session_duration_minutes(self):
        return duration_minutes_for_times(
            self.cleaned_data["hora_sessao_inicial"],
            self.cleaned_data["hora_fim_sessao_inicial"],
        )


class SessaoForm(forms.ModelForm):
    hora_final = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
        label="Horário final",
    )

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
        self.fields["hora_final"].input_formats = ["%H:%M"]

        if self.instance and self.instance.pk and self.instance.data_hora:
            self.fields["hora_final"].initial = self.instance.data_hora_fim.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        data_hora = cleaned_data.get("data_hora")
        hora_final = cleaned_data.get("hora_final")

        if data_hora and not hora_final:
            self.add_error("hora_final", "Informe o horário final da sessão.")

        if data_hora and hora_final:
            hora_inicial = data_hora.time()
            if hora_final <= hora_inicial:
                self.add_error("hora_final", "O horário final deve ser maior que o horário inicial.")

        return cleaned_data

    def get_duration_minutes(self):
        return duration_minutes_for_datetime_end(
            self.cleaned_data["data_hora"],
            self.cleaned_data["hora_final"],
        )


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
        help_text="Define a duração de cada sessão gerada neste período.",
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

        if hora_inicial and not hora_final:
            self.add_error("hora_final", "Informe o horário final das sessões deste período.")
        if hora_inicial and hora_final and hora_final <= hora_inicial:
            self.add_error("hora_final", "O horário final deve ser maior que o horário inicial.")

        return cleaned_data


class TipoProcedimentoForm(forms.ModelForm):
    class Meta:
        model = TipoProcedimento
        fields = ["nome", "habilita_exercicios"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Pilates"}),
            "habilita_exercicios": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nome": "Nome",
            "habilita_exercicios": "Habilita gerenciamento de exercícios",
        }

