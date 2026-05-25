from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..forms import SessaoForm
from ..models import Procedimento, Sessao
from ..services.procedures import update_session_status
from ..services.scheduling import create_session_for_procedimento, update_sessao


@login_required
@require_POST
def add_sessao(request, pk):
    procedimento = get_object_or_404(Procedimento, pk=pk)
    form = SessaoForm(request.POST)
    if form.is_valid():
        try:
            create_session_for_procedimento(
                procedimento,
                data_hora=form.cleaned_data["data_hora"],
                duracao_minutos=form.get_duration_minutes(),
                status=form.cleaned_data["status"],
                assinatura_confirmada=form.cleaned_data["assinatura_confirmada"],
                observacoes=form.cleaned_data["observacoes"],
            )
            messages.success(request, "Sessão adicionada com sucesso.")
        except ValidationError as exc:
            messages.warning(request, exc.message)
    else:
        messages.error(request, "Não foi possível adicionar a sessão. Verifique os dados informados.")
    return redirect("procedure-detail", pk=procedimento.pk)


@login_required
@require_POST
def edit_sessao(request, session_id):
    sessao = get_object_or_404(Sessao, pk=session_id)
    form = SessaoForm(request.POST, instance=sessao)
    if form.is_valid():
        try:
            update_sessao(
                sessao,
                data_hora=form.cleaned_data["data_hora"],
                duracao_minutos=form.get_duration_minutes(),
                status=form.cleaned_data["status"],
                assinatura_confirmada=form.cleaned_data["assinatura_confirmada"],
                observacoes=form.cleaned_data["observacoes"],
            )
            messages.success(request, "Sessão atualizada com sucesso.")
        except ValidationError as exc:
            messages.warning(request, exc.message)
    else:
        messages.error(request, "Não foi possível atualizar a sessão.")
    return redirect("procedure-detail", pk=sessao.procedimento_id)


@login_required
@require_POST
def update_status_sessao(request, session_id, status):
    sessao = get_object_or_404(Sessao, pk=session_id)
    try:
        update_session_status(sessao, status)
    except ValidationError as exc:
        messages.error(request, exc.message)
        return redirect("procedure-detail", pk=sessao.procedimento_id)

    messages.success(request, "Status da sessão atualizado com sucesso.")
    return redirect("procedure-detail", pk=sessao.procedimento_id)

