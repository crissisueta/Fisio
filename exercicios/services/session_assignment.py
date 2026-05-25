from __future__ import annotations

from django.db import transaction

from ..models import ExercicioCatalogo, SessaoExercicio
from procedimentos.models import Procedimento, Sessao


def get_default_exercise_ids_for_session(sessao: Sessao) -> list[int]:
    return list(
        sessao.procedimento.procedimento_exercicios.filter(is_active=True).values_list("exercicio_id", flat=True)
    )


@transaction.atomic
def assign_exercises_to_session(sessao: Sessao, exercicios_selecionados: list[ExercicioCatalogo]) -> None:
    procedimento: Procedimento = sessao.procedimento
    legacy_items = list(procedimento.procedimento_exercicios.filter(is_active=True).select_related("exercicio"))
    legacy_by_exercicio = {item.exercicio_id: item for item in legacy_items}
    selecionados_ids = {exercicio.pk for exercicio in exercicios_selecionados}
    existentes = {
        item.exercicio_id: item
        for item in SessaoExercicio.all_objects.filter(sessao=sessao).select_related("exercicio")
    }

    for ordem, exercicio in enumerate(exercicios_selecionados, start=1):
        item = existentes.get(exercicio.pk)
        if item:
            update_fields = []
            if not item.is_active:
                item.is_active = True
                item.deleted_at = None
                update_fields.extend(["is_active", "deleted_at"])
            if item.ordem != ordem:
                item.ordem = ordem
                update_fields.append("ordem")
            if update_fields:
                if hasattr(item, "updated_at"):
                    update_fields.append("updated_at")
                item.save(update_fields=update_fields)
            continue

        legacy_item = legacy_by_exercicio.get(exercicio.pk)
        SessaoExercicio.objects.create(
            sessao=sessao,
            exercicio=exercicio,
            ordem=ordem,
            series=legacy_item.series if legacy_item else "",
            repeticoes=legacy_item.repeticoes if legacy_item else "",
            frequencia=legacy_item.frequencia if legacy_item else "",
            progressao=legacy_item.progressao if legacy_item else "",
            observacoes=legacy_item.observacoes if legacy_item else "",
            status=legacy_item.status if legacy_item else SessaoExercicio.STATUS_PLANEJADO,
        )

    ids_para_desativar = [
        item.pk
        for exercicio_id, item in existentes.items()
        if exercicio_id not in selecionados_ids and item.is_active
    ]
    if ids_para_desativar:
        SessaoExercicio.objects.filter(pk__in=ids_para_desativar).delete()

