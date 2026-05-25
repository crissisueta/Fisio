from django.db import migrations


def _existing_table_names(schema_editor):
    with schema_editor.connection.cursor() as cursor:
        return set(schema_editor.connection.introspection.table_names(cursor))


def _existing_column_names(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        return {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }


def _existing_constraint_names(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        return set(schema_editor.connection.introspection.get_constraints(cursor, table_name))


class CreateModelIfNotExists(migrations.CreateModel):
    """Create the table on fresh databases and skip it when a legacy table exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        if model._meta.db_table in _existing_table_names(schema_editor):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class AddFieldIfMissing(migrations.AddField):
    """Add a column on fresh databases and skip it when a legacy column exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        field = model._meta.get_field(self.name)
        if field.column in _existing_column_names(schema_editor, model._meta.db_table):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class AddConstraintIfNotExists(migrations.AddConstraint):
    """Add a constraint on fresh databases and skip it when a legacy constraint exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.constraint.name in _existing_constraint_names(schema_editor, model._meta.db_table):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)
