from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


def migrate_exercise_categories(apps, schema_editor):
    CategoriaExercicio = apps.get_model("forms", "CategoriaExercicio")
    ExercicioCatalogo = apps.get_model("forms", "ExercicioCatalogo")

    categoria_padrao, _ = CategoriaExercicio.objects.get_or_create(
        nome="Sem categoria",
        defaults={"descricao": "Categoria criada automaticamente para exercícios legados sem classificação."},
    )

    for exercicio in ExercicioCatalogo.objects.all():
        nome_categoria = (getattr(exercicio, "categoria_legado", "") or "").strip()
        if nome_categoria:
            categoria, _ = CategoriaExercicio.objects.get_or_create(nome=nome_categoria)
        else:
            categoria = categoria_padrao
        exercicio.categoria_id = categoria.pk
        exercicio.save(update_fields=["categoria"])


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0018_exerciciocatalogo_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategoriaExercicio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("descricao", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Categoria de Exercício",
                "verbose_name_plural": "Categorias de Exercícios",
                "ordering": ["nome"],
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.RenameField(
            model_name="exerciciocatalogo",
            old_name="categoria",
            new_name="categoria_legado",
        ),
        migrations.AddField(
            model_name="exerciciocatalogo",
            name="categoria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="exercicios",
                to="forms.categoriaexercicio",
            ),
        ),
        migrations.RunPython(migrate_exercise_categories, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="exerciciocatalogo",
            name="categoria_legado",
        ),
        migrations.AlterField(
            model_name="exerciciocatalogo",
            name="categoria",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="exercicios",
                to="forms.categoriaexercicio",
            ),
        ),
    ]
