from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """Modelo base abstrato com timestamps automáticos."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet com suporte a soft delete em lote."""

    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def delete(self):
        return self.soft_delete()

    def soft_delete(self):
        timestamp = timezone.now()
        updated = self.filter(is_active=True).update(is_active=False, deleted_at=timestamp)
        return updated, {self.model._meta.label: updated}

    def hard_delete(self):
        return super().delete()


class ActiveManager(models.Manager):
    """Manager padrão que expõe somente registros ativos."""

    def get_queryset(self):
        queryset = SoftDeleteQuerySet(self.model, using=self._db).active()
        related_filters = getattr(self.model, "ACTIVE_RELATED_FILTERS", {})
        if related_filters:
            queryset = queryset.filter(**related_filters)
        return queryset


class AllObjectsManager(models.Manager):
    """Manager para acesso administrativo/debug a todos os registros."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """Modelo base abstrato com desativação lógica."""

    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"
        default_manager_name = "objects"

    def delete(self, using=None, keep_parents=False):
        if not self.is_active:
            return 0, {}

        self.is_active = False
        self.deleted_at = timezone.now()
        update_fields = ["is_active", "deleted_at"]

        if hasattr(self, "updated_at"):
            self.updated_at = self.deleted_at
            update_fields.append("updated_at")

        self.save(update_fields=update_fields)
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_active = True
        self.deleted_at = None
        update_fields = ["is_active", "deleted_at"]

        if hasattr(self, "updated_at"):
            self.updated_at = timezone.now()
            update_fields.append("updated_at")

        self.save(update_fields=update_fields)



class ActivityLog(models.Model):
    """Registro simples de ações importantes do sistema."""

    LEVEL_INFO = "info"
    LEVEL_SUCCESS = "success"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"

    LEVEL_CHOICES = [
        (LEVEL_INFO, "Info"),
        (LEVEL_SUCCESS, "Success"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_ERROR, "Error"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )
    event_type = models.CharField(max_length=100)
    message = models.CharField(max_length=500)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["event_type"]),
        ]
        verbose_name = "Registro de atividade"
        verbose_name_plural = "Registros de atividade"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} - {self.message}"

    @property
    def actor_name(self):
        if not self.user_id or not self.user:
            return "Sistema"
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.get_username()
