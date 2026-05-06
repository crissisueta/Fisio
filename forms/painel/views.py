from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .selectors import get_dashboard_counts


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_dashboard_counts())
        return context

