from django import forms

from .services import TARGET_CHOICES


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file_data, initial) for file_data in data]
        return [single_file_clean(data, initial)]


class SpreadsheetImportForm(forms.Form):
    target = forms.ChoiceField(
        choices=TARGET_CHOICES,
        label="Destino",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    arquivo = MultipleFileField(
        label="Arquivos",
        widget=MultipleFileInput(attrs={"class": "form-control", "accept": ".xlsx,.csv", "multiple": True}),
    )
    sheet_name = forms.CharField(
        required=False,
        label="Aba",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Primeira aba"}),
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=True,
        label="Atualizar existentes",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    create_related = forms.BooleanField(
        required=False,
        initial=True,
        label="Criar cadastros relacionados",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label="Simular sem salvar",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_arquivo(self):
        arquivos = self.cleaned_data["arquivo"]
        for arquivo in arquivos:
            name = arquivo.name.lower()
            if not (name.endswith(".xlsx") or name.endswith(".csv")):
                raise forms.ValidationError("Envie apenas arquivos .xlsx ou .csv.")
        return arquivos
