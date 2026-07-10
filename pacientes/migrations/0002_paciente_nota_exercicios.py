from django.db import migrations, models

from core.migration_operations import AddFieldIfMissing


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0001_initial"),
    ]

    operations = [
        AddFieldIfMissing(
            model_name="paciente",
            name="nota_exercicios",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
