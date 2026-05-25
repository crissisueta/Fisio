from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission


LEGACY_MODEL_APP_LABELS = {
    "paciente": "pacientes",
    "tipoavaliacao": "avaliacoes",
    "avaliacao": "avaliacoes",
    "tipoprocedimento": "procedimentos",
    "procedimento": "procedimentos",
    "sessao": "procedimentos",
    "fichaexercicios": "exercicios",
    "categoriaexercicio": "exercicios",
    "exerciciocatalogo": "exercicios",
    "procedimentoexercicio": "exercicios",
    "sessaoexercicio": "exercicios",
}


def copy_legacy_permission_assignments(sender, using, **kwargs):
    legacy_permissions = (
        Permission.objects.using(using)
        .filter(content_type__app_label="forms")
        .select_related("content_type")
    )

    for legacy_permission in legacy_permissions:
        new_app_label = LEGACY_MODEL_APP_LABELS.get(legacy_permission.content_type.model)
        if not new_app_label:
            continue

        new_permission = (
            Permission.objects.using(using)
            .filter(
                codename=legacy_permission.codename,
                content_type__app_label=new_app_label,
                content_type__model=legacy_permission.content_type.model,
            )
            .first()
        )
        if new_permission is None:
            continue

        _copy_user_permission(legacy_permission, new_permission, using)
        _copy_group_permission(legacy_permission, new_permission, using)


def _copy_user_permission(legacy_permission, new_permission, using):
    User = get_user_model()
    through = User.user_permissions.through
    user_ids = list(
        through.objects.using(using)
        .filter(permission_id=legacy_permission.pk)
        .values_list("user_id", flat=True)
    )
    through.objects.using(using).bulk_create(
        [through(user_id=user_id, permission_id=new_permission.pk) for user_id in user_ids],
        ignore_conflicts=True,
    )


def _copy_group_permission(legacy_permission, new_permission, using):
    through = Group.permissions.through
    group_ids = list(
        through.objects.using(using)
        .filter(permission_id=legacy_permission.pk)
        .values_list("group_id", flat=True)
    )
    through.objects.using(using).bulk_create(
        [through(group_id=group_id, permission_id=new_permission.pk) for group_id in group_ids],
        ignore_conflicts=True,
    )
