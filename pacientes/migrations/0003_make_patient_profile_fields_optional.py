from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0002_paciente_nota_exercicios"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paciente",
            name="cpf",
            field=models.CharField(blank=True, max_length=14, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="endereco",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="bairro",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="cep",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="celular",
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="data_matricula",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="plano",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
