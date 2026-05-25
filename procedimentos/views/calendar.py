from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView

from ..forms import ProcedimentoForm
from ..presenters.calendar import build_calendar_events
from .mixins import ProcedureCreateFlowMixin


def calendar_events(request):
    events = build_calendar_events()
    return JsonResponse(events, safe=False)


class CalendarDashboardView(ProcedureCreateFlowMixin, LoginRequiredMixin, TemplateView):
    template_name = "dashboard/calendar.html"

    def get_form(self, data=None):
        return ProcedimentoForm(
            data=data,
            enable_schedule_fields=True,
            initial=self.get_procedure_initial(),
        )

    def get_procedure_initial(self):
        initial = {}
        selected_date = self.request.GET.get("date", "").strip()
        if selected_date:
            initial["data_sessao_inicial"] = selected_date
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["procedure_form"] = kwargs.get("procedure_form") or self.get_form()
        context["selected_calendar_date"] = self.request.GET.get("date", "").strip()
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST)
        if form.is_valid():
            response = self.handle_valid_procedure_form(form)
            if response is not None:
                return response
        return self.render_to_response(self.get_context_data(procedure_form=form))

