import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import SoftDeleteSuccessMessageMixin
from core.models import ActivityLog
from core.services.activity import log_activity
from exercicios.presenters.monthly_tracking import present_monthly_tracking_table
from exercicios.services.monthly_tracking import (
    build_monthly_exercise_tracking_table,
    mark_exercise_day_for_patient,
    parse_month_reference,
    unmark_exercise_day_for_patient,
)
from .forms import PacienteForm
from .models import Paciente
from .selectors import get_paciente_detail_context, serialize_paciente_summary


@login_required
def get_paciente_data(request, paciente_id):
    paciente = get_object_or_404(Paciente, pk=paciente_id)
    return JsonResponse(serialize_paciente_summary(paciente))


@login_required
@require_POST
def mark_paciente_exercise_day(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError
        exercise_id = int(payload.get("exercise_id"))
        target_date = parse_date(payload.get("date") or "")
        action = payload.get("action", "mark")
        if target_date is None:
            raise ValueError
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Informe exercício e data válidos."}, status=400)

    try:
        if action == "unmark":
            result = unmark_exercise_day_for_patient(
                paciente,
                exercise_id=exercise_id,
                target_date=target_date,
            )
            return JsonResponse(
                {
                    "success": True,
                    "action": "unmark",
                    "exercise_id": result.exercise_id,
                    "date": result.target_date.isoformat(),
                    "session_id": result.sessao_id,
                    "deleted_session": result.deleted_session,
                }
            )
        if action != "mark":
            raise ValidationError("Ação inválida.")

        result = mark_exercise_day_for_patient(paciente, exercise_id=exercise_id, target_date=target_date)
    except ObjectDoesNotExist:
        return JsonResponse({"success": False, "error": "Exercício não encontrado."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"success": False, "error": " ".join(exc.messages)}, status=400)

    return JsonResponse(
        {
            "success": True,
            "action": "mark",
            "exercise_id": result.sessao_exercicio.exercicio_id,
            "date": result.target_date.isoformat(),
            "session_id": result.sessao.pk,
            "session_status": result.sessao.status,
            "created_session": result.created_session,
            "created_link": result.created_link,
        }
    )


@login_required
@require_POST
def update_paciente_exercise_note(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    note = request.POST.get("nota_exercicios", "").strip()
    max_length = Paciente._meta.get_field("nota_exercicios").max_length
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if len(note) > max_length:
        error = f"A nota deve ter no máximo {max_length} caracteres."
        if is_ajax:
            return JsonResponse({"success": False, "error": error}, status=400)
        messages.error(request, error)
    else:
        paciente.nota_exercicios = note
        paciente.save(update_fields=["nota_exercicios", "updated_at"])
        if is_ajax:
            return JsonResponse({"success": True, "nota_exercicios": note})
        messages.success(request, "Nota de exercícios salva.")

    detail_url = reverse("inscricao-detail", args=[paciente.pk])
    month = request.POST.get("month", "").strip()
    if month:
        detail_url = f"{detail_url}?month={month}"
    return redirect(detail_url)


class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = "forms/inscricao_list.html"
    context_object_name = "fichas"
    paginate_by = 100

    def get_queryset(self):
        queryset = super().get_queryset()
        self.search_query = self.request.GET.get("q", "").strip()
        if self.search_query:
            queryset = queryset.filter(
                Q(nome__icontains=self.search_query)
                | Q(cpf__icontains=self.search_query)
                | Q(email__icontains=self.search_query)
                | Q(telefone__icontains=self.search_query)
                | Q(celular__icontains=self.search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = getattr(self, "search_query", "")
        context["search_query"] = search_query
        context["pagination_query"] = f"{urlencode({'q': search_query})}&" if search_query else ""
        return context


class PacienteDetailView(LoginRequiredMixin, DetailView):
    model = Paciente
    template_name = "forms/inscricao_detail.html"
    context_object_name = "ficha"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_paciente_detail_context(self.object))
        month = parse_month_reference(self.request.GET.get("month"))
        tracking = build_monthly_exercise_tracking_table(self.object, month)
        next_tracking = build_monthly_exercise_tracking_table(self.object, tracking.next_month_param)
        context["exercise_tracking"] = present_monthly_tracking_table(tracking, next_tracking)
        return context


class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Paciente cadastrado com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="patient.created",
            message=f"cadastrou paciente {self.object.nome}",
            level=ActivityLog.LEVEL_SUCCESS,
            metadata={"patient_id": self.object.pk},
        )
        return response


class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do paciente atualizado com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="patient.updated",
            message=f"atualizou cadastro de {self.object.nome}",
            level=ActivityLog.LEVEL_INFO,
            metadata={"patient_id": self.object.pk},
        )
        return response


class PacienteDeleteView(SoftDeleteSuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = "forms/inscricao_confirm_delete.html"
    success_url = reverse_lazy("inscricao-list")
    delete_success_message = "Paciente removido com sucesso."

    def form_valid(self, form):
        patient_id = self.object.pk
        patient_name = self.object.nome
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="patient.deleted",
            message=f"removeu paciente {patient_name}",
            level=ActivityLog.LEVEL_WARNING,
            metadata={"patient_id": patient_id},
        )
        return response
