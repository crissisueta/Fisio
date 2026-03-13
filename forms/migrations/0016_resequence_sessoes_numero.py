from django.db import migrations


def resequence_sessoes(apps, schema_editor):
    Sessao = apps.get_model("forms", "Sessao")

    procedimento_ids = (
        Sessao.objects.order_by()
        .values_list("procedimento_id", flat=True)
        .distinct()
    )

    for procedimento_id in procedimento_ids:
        sessoes = list(
            Sessao.objects.filter(procedimento_id=procedimento_id)
            .order_by("data_hora", "created_at", "id")
        )
        for index, sessao in enumerate(sessoes, start=1):
            if sessao.numero != index:
                sessao.numero = index
                sessao.save(update_fields=["numero"])


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0015_fichaexercicios"),
    ]

    operations = [
        migrations.RunPython(resequence_sessoes, migrations.RunPython.noop),
    ]
