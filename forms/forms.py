from django import forms

from .models import FichaInscricao, Procedure, ProcedureSession


class FichaInscricaoForm(forms.ModelForm):
    class Meta:
        model = FichaInscricao
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
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
            "profissao": forms.TextInput(attrs={"class": "form-control"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "bairro": forms.TextInput(attrs={"class": "form-control"}),
            "cep": forms.TextInput(attrs={"class": "form-control", "placeholder": "00000-000"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "celular": forms.TextInput(attrs={"class": "form-control"}),
            "telefone_comercial": forms.TextInput(attrs={"class": "form-control"}),
            "data_nascimento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_matricula": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "plano": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class ProcedureForm(forms.ModelForm):
    class Meta:
        model = Procedure
        fields = ["patient", "procedure_type", "observacoes", "is_complete"]
        widgets = {
            "patient": forms.Select(attrs={"class": "form-select"}),
            "procedure_type": forms.Select(attrs={"class": "form-select"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_complete": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "patient": "Paciente",
            "procedure_type": "Tipo de Procedimento",
            "observacoes": "Observações",
            "is_complete": "Concluído",
        }


class ProcedureSessionForm(forms.ModelForm):
    class Meta:
        model = ProcedureSession
        fields = ["scheduled_datetime", "status", "notes"]
        widgets = {
            "scheduled_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "scheduled_datetime": "Data e Hora",
            "status": "Status da Sessão",
            "notes": "Notas",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
