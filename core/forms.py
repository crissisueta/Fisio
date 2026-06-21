from django import forms


class FeedbackForm(forms.Form):
    TYPE_CHOICES = (
        ("bug", "Erro"),
        ("suggestion", "Sugestao"),
    )

    feedback_type = forms.ChoiceField(choices=TYPE_CHOICES, required=False)
    message = forms.CharField(max_length=4000)
    source_page = forms.CharField(max_length=2048, required=False)
    website = forms.CharField(required=False)

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if not message:
            raise forms.ValidationError("Escreva uma mensagem antes de enviar.")
        return message

    def clean_source_page(self):
        return self.cleaned_data.get("source_page", "").strip()

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Envio invalido.")
        return ""
