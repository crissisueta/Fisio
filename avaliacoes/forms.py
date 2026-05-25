from django import forms

from .models import Avaliacao


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

