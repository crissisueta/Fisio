from django import forms
from django.conf import settings


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
    arquivo = MultipleFileField(
        label="Planilhas",
        widget=MultipleFileInput(attrs={"class": "form-control", "accept": ".xlsx", "multiple": True}),
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
        max_files = getattr(settings, "IMPORTACAO_WEB_MAX_FILES", 1)
        if max_files and len(arquivos) > max_files:
            raise forms.ValidationError(
                "A importacao web aceita no maximo %(max_files)s arquivo(s). "
                "Para lotes maiores, use o comando python manage.py importar_historicos.",
                params={"max_files": max_files},
            )
        for arquivo in arquivos:
            name = arquivo.name.lower()
            if not name.endswith(".xlsx"):
                raise forms.ValidationError("Envie apenas arquivos .xlsx.")
        return arquivos
