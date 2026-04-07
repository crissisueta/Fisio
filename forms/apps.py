from django.apps import AppConfig


class FormsConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = 'forms'
    verbose_name = 'Formulários de Fisioterapia'
