from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0010_migrate_legacy_procedures_data"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AnamneseAcupuntura",
        ),
        migrations.DeleteModel(
            name="AnamneseGeral",
        ),
        migrations.DeleteModel(
            name="FichaDrenagem",
        ),
        migrations.DeleteModel(
            name="FichaExercicios",
        ),
        migrations.DeleteModel(
            name="FollowUpSession",
        ),
    ]
