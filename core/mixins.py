from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class InternalPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Você não possui permissão para acessar esta área.")
        return super().handle_no_permission()


class SoftDeleteSuccessMessageMixin:
    """Keeps delete messages compatible with Django 4.2's DeleteView flow."""

    delete_success_message = ""

    def form_valid(self, form):
        if self.delete_success_message:
            messages.success(self.request, self.delete_success_message)
        return super().form_valid(form)

