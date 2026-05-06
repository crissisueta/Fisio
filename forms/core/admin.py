from django.contrib import admin


class SoftDeleteAdminMixin:
    """Admin que exibe status e converte deleções em soft delete."""

    actions = ("soft_delete_selected",)

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()

    @admin.action(description="Desativar selecionados")
    def soft_delete_selected(self, request, queryset):
        queryset.delete()

    def delete_model(self, request, obj):
        obj.delete()

    def delete_queryset(self, request, queryset):
        queryset.delete()

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

