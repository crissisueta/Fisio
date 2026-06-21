from django import forms

from .services import TARGET_CHOICES


class SpreadsheetImportForm(forms.Form):
    target = forms.ChoiceField(
        choices=TARGET_CHOICES,
        label="Destino",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    arquivo = forms.FileField(
        label="Arquivo",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".xlsx,.csv"}),
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
        arquivo = self.cleaned_data["arquivo"]
        name = arquivo.name.lower()
        if not (name.endswith(".xlsx") or name.endswith(".csv")):
            raise forms.ValidationError("Envie um arquivo .xlsx ou .csv.")
        return arquivo

