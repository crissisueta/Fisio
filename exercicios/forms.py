from itertools import groupby

from django import forms
from django.db.models import Q

from .models import CategoriaExercicio, ExercicioCatalogo


class SessaoExercicioSelectionForm(forms.Form):
    exercicios = forms.ModelMultipleChoiceField(
        queryset=ExercicioCatalogo.objects.filter(ativo=True).order_by("nome"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Exercícios disponíveis",
    )

    def __init__(self, *args, **kwargs):
        sessao = kwargs.pop("sessao")
        selected_ids = kwargs.pop("selected_ids", None)
        super().__init__(*args, **kwargs)
        self.sessao = sessao
        self.fields["exercicios"].queryset = (
            ExercicioCatalogo.objects.filter(
                is_active=True,
                ativo=True,
            )
            .select_related("categoria")
            .order_by("categoria__nome", "nome")
        )
        if selected_ids is None:
            selected_ids = list(sessao.sessao_exercicios.filter(is_active=True).values_list("exercicio_id", flat=True))
        self.fields["exercicios"].initial = list(selected_ids)

    def get_exercicios_agrupados(self, exercise_status_map=None):
        queryset = list(self.fields["exercicios"].queryset)
        return [
            {
                "categoria": categoria,
                "exercicios": [
                    {
                        "obj": exercicio,
                        "status": (exercise_status_map or {}).get(exercicio.pk),
                    }
                    for exercicio in exercicios
                ],
            }
            for categoria, exercicios in groupby(queryset, key=lambda exercicio: exercicio.categoria)
        ]


class CategoriaExercicioForm(forms.ModelForm):
    class Meta:
        model = CategoriaExercicio
        fields = ["nome", "descricao"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Alongamento"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
        labels = {
            "nome": "Nome",
            "descricao": "Descrição",
        }


class ExercicioCatalogoForm(forms.ModelForm):
    class Meta:
        model = ExercicioCatalogo
        fields = [
            "nome",
            "categoria",
            "descricao",
            "instrucoes",
            "observacoes",
            "ativo",
            "max_sessoes_consecutivas",
            "sessoes_ate_cooldown",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Ponte pélvica"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "instrucoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "max_sessoes_consecutivas": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "sessoes_ate_cooldown": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }
        labels = {
            "nome": "Nome",
            "categoria": "Categoria",
            "descricao": "Descrição",
            "instrucoes": "Instruções",
            "observacoes": "Observações",
            "ativo": "Disponível para uso",
            "max_sessoes_consecutivas": "Máximo de sessões consecutivas",
            "sessoes_ate_cooldown": "Sessões até sair do cooldown",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = CategoriaExercicio.objects.order_by("nome")
        instance = getattr(self, "instance", None)
        categoria_atual_id = getattr(instance, "categoria_id", None)

        if categoria_atual_id:
            queryset = CategoriaExercicio.all_objects.filter(Q(is_active=True) | Q(pk=categoria_atual_id)).order_by(
                "nome"
            )

        self.fields["categoria"].queryset = queryset

