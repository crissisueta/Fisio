from django import forms
from .models import (
    FichaInscricao, AnamneseGeral, AnamneseAcupuntura,
    FichaDrenagem, FichaExercicios
)


class FichaInscricaoForm(forms.ModelForm):
    class Meta:
        model = FichaInscricao
        fields = [
            'nome', 'cpf', 'email', 'profissao', 'endereco', 'bairro', 'cep',
            'telefone', 'celular', 'telefone_comercial', 'data_nascimento',
            'data_matricula', 'plano', 'observacoes'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone_comercial': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_matricula': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'plano': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class AnamneseGeralForm(forms.ModelForm):
    class Meta:
        model = AnamneseGeral
        fields = [
            'paciente', 'nome', 'profissao', 'data_nascimento', 'data',
            'diabetes', 'anemia', 'hipoglicemia', 'pressao_alta', 'pressao_baixa',
            'problema_cardiaco', 'usa_medicamentos', 'observacoes'
        ]
        labels = {
            'data': 'Data de Avaliação',
            'data_nascimento': 'Data de Nascimento',
        }
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control', 'id': 'id_paciente'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'diabetes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anemia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hipoglicemia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pressao_alta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pressao_baixa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'problema_cardiaco': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usa_medicamentos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # make sure the datetime-local widget value is parsed with both date and time
        self.fields['data'].input_formats = ['%Y-%m-%dT%H:%M']


class AnamneseAcupunturaForm(forms.ModelForm):
    class Meta:
        model = AnamneseAcupuntura
        fields = [
            'paciente', 'nome', 'data_consulta', 'endereco', 'telefone', 'data_nascimento',
            'profissao', 'religiao', 'idade', 'estado_civil', 'filhos',
            'ja_fez_acupuntura', 'queixa_principal', 'historia_doenca_atual',
            'medicacao', 'historia_patologica_pregressa', 'doencas_familia',
            'rotina_diaria', 'atividade_fisica', 'sono', 'emocao_predominante',
            'sabor_preferido', 'pulso_direito', 'pulso_esquerdo', 'lingua',
            'diagnostico', 'prescricao', 'observacoes'
        ]
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control', 'id': 'id_paciente'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_consulta': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
            'religiao': forms.TextInput(attrs={'class': 'form-control'}),
            'idade': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado_civil': forms.TextInput(attrs={'class': 'form-control'}),
            'filhos': forms.TextInput(attrs={'class': 'form-control'}),
            'ja_fez_acupuntura': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'queixa_principal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'historia_doenca_atual': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medicacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'historia_patologica_pregressa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'doencas_familia': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rotina_diaria': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'atividade_fisica': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sono': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emocao_predominante': forms.TextInput(attrs={'class': 'form-control'}),
            'sabor_preferido': forms.TextInput(attrs={'class': 'form-control'}),
            'pulso_direito': forms.TextInput(attrs={'class': 'form-control'}),
            'pulso_esquerdo': forms.TextInput(attrs={'class': 'form-control'}),
            'lingua': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prescricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_consulta'].input_formats = ['%Y-%m-%dT%H:%M']


class FichaDrenagemForm(forms.ModelForm):
    class Meta:
        model = FichaDrenagem
        fields = [
            'paciente', 'nome', 'endereco', 'telefone', 'convenio', 'data_nascimento',
            'idade', 'altura', 'peso', 'data', 'queixa',
            'historia_doenca_atual', 'avaliacao', 'historia_patologica_pregressa'
        ]
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control', 'id': 'id_paciente'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'convenio': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'idade': forms.NumberInput(attrs={'class': 'form-control'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'data': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'queixa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'historia_doenca_atual': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avaliacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'historia_patologica_pregressa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data'].input_formats = ['%Y-%m-%dT%H:%M']


class FichaExerciciosForm(forms.ModelForm):
    class Meta:
        model = FichaExercicios
        fields = [
            'paciente', 'aluno', 'objetivo', 'historico_patologico', 'flexibilidade',
            'dominancia_muscular', 'observacoes', 'dia', 'mes'
        ]
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control', 'id': 'id_paciente'}),
            'aluno': forms.TextInput(attrs={'class': 'form-control'}),
            'objetivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'historico_patologico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'flexibilidade': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dominancia_muscular': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dia': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'mes': forms.TextInput(attrs={'class': 'form-control', 'type': 'month'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dia'].input_formats = ['%Y-%m-%dT%H:%M']
