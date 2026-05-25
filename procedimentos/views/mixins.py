from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

from ..forms import ProcedimentoForm
from ..services.procedures import save_procedure_with_optional_initial_session


class ProcedureCreateFlowMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["enable_schedule_fields"] = True
        return kwargs

    def handle_valid_procedure_form(self, form):
        try:
            modo_agendamento = form.cleaned_data["modo_agendamento"]
            schedule_initial = modo_agendamento == ProcedimentoForm.MODO_AGENDAMENTO_UNICO
            result = save_procedure_with_optional_initial_session(
                form.save(commit=False),
                create_initial_session=schedule_initial,
                initial_session_datetime=form.get_initial_session_datetime() if schedule_initial else None,
                initial_session_duration_minutes=form.get_initial_session_duration_minutes() if schedule_initial else None,
            )
            self.object = result.procedimento
        except ValidationError as exc:
            form.add_error("hora_sessao_inicial", exc.message)
            return None

        if form.cleaned_data["modo_agendamento"] == ProcedimentoForm.MODO_AGENDAMENTO_UNICO:
            messages.success(self.request, "Procedimento criado com sucesso com a primeira sessão agendada.")
            return redirect("procedure-detail", pk=self.object.pk)

        messages.success(self.request, "Procedimento criado com sucesso. Agora preencha o período das sessões.")
        return redirect("procedure-bulk-schedule", pk=self.object.pk)
