from django import forms

from .models import Avaliacao, Paciente, Procedimento, Sessao


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


class SessaoForm(forms.ModelForm):
    class Meta:
        model = Sessao
        fields = ["data_hora", "numero", "status", "assinatura_confirmada", "observacoes"]
        widgets = {
            "data_hora": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "numero": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "assinatura_confirmada": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "data_hora": "Data e Hora",
            "numero": "Número da Sessão",
            "status": "Status",
            "assinatura_confirmada": "Assinatura Confirmada",
            "observacoes": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora"].input_formats = ["%Y-%m-%dT%H:%M"]
