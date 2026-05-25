from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Infraestrutura"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .permissions import copy_legacy_permission_assignments

        post_migrate.connect(
            copy_legacy_permission_assignments,
            dispatch_uid="core.copy_legacy_permission_assignments",
        )
