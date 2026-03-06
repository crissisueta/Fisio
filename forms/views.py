from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    FichaInscricao, AnamneseGeral, AnamneseAcupuntura,
    FichaDrenagem, FichaExercicios
)
from .forms import (
    FichaInscricaoForm, AnamneseGeralForm, AnamneseAcupunturaForm,
    FichaDrenagemForm, FichaExerciciosForm
)
from .services.calendar_service import build_calendar_events


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inscricoes_count'] = FichaInscricao.objects.count()
        context['anamneses_count'] = AnamneseGeral.objects.count()
        context['acupuntura_count'] = AnamneseAcupuntura.objects.count()
        context['drenagem_count'] = FichaDrenagem.objects.count()
        context['exercicios_count'] = FichaExercicios.objects.count()
        return context


@login_required

def get_paciente_data(request, paciente_id):
    """API endpoint para retornar dados do paciente em JSON"""
    try:
        paciente = FichaInscricao.objects.get(pk=paciente_id)
        return JsonResponse({
            'nome': paciente.nome,
            'profissao': paciente.profissao,
            'data_nascimento': paciente.data_nascimento.isoformat(),
            'endereco': paciente.endereco,
            'telefone': paciente.telefone,
            'celular': paciente.celular,
            'idade': (timezone.now().date() - paciente.data_nascimento).days // 365,  # idade estimada
        })
    except FichaInscricao.DoesNotExist:
        return JsonResponse({'error': 'Paciente não encontrado'}, status=404)


# FichaInscricao Views
class FichaInscricaoListView(LoginRequiredMixin, ListView):
    model = FichaInscricao
    template_name = 'forms/inscricao_list.html'
    context_object_name = 'fichas'
    paginate_by = 10


class FichaInscricaoDetailView(LoginRequiredMixin, DetailView):
    model = FichaInscricao
    template_name = 'forms/inscricao_detail.html'
    context_object_name = 'ficha'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ficha = self.get_object()
        context['anamneses_geral'] = ficha.anamneses_geral.all()
        context['anamneses_acupuntura'] = ficha.anamneses_acupuntura.all()
        context['fichas_drenagem'] = ficha.fichas_drenagem.all()
        context['fichas_exercicios'] = ficha.fichas_exercicios.all()
        return context


class FichaInscricaoCreateView(LoginRequiredMixin, CreateView):
    model = FichaInscricao
    form_class = FichaInscricaoForm
    template_name = 'forms/inscricao_form.html'
    success_url = reverse_lazy('inscricao-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Inscrição criada com sucesso!')
        return super().form_valid(form)


class FichaInscricaoUpdateView(LoginRequiredMixin, UpdateView):
    model = FichaInscricao
    form_class = FichaInscricaoForm
    template_name = 'forms/inscricao_form.html'
    success_url = reverse_lazy('inscricao-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Inscrição atualizada com sucesso!')
        return super().form_valid(form)


class FichaInscricaoDeleteView(LoginRequiredMixin, DeleteView):
    model = FichaInscricao
    template_name = 'forms/inscricao_confirm_delete.html'
    success_url = reverse_lazy('inscricao-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Ficha de Inscrição deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# AnamneseGeral Views
class AnamneseGeralListView(LoginRequiredMixin, ListView):
    model = AnamneseGeral
    template_name = 'forms/anamnese_geral_list.html'
    context_object_name = 'fichas'
    paginate_by = 10


class AnamneseGeralDetailView(LoginRequiredMixin, DetailView):
    model = AnamneseGeral
    template_name = 'forms/anamnese_geral_detail.html'
    context_object_name = 'ficha'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        from django.contrib.contenttypes.models import ContentType
        from .models import FollowUpSession
        ct = ContentType.objects.get_for_model(obj)
        context['sessions'] = FollowUpSession.objects.filter(content_type=ct, object_id=obj.pk).order_by('session_date')
        context['model_slug'] = 'anamnese-geral'
        return context


class AnamneseGeralCreateView(LoginRequiredMixin, CreateView):
    model = AnamneseGeral
    form_class = AnamneseGeralForm
    template_name = 'forms/anamnese_geral_form.html'
    success_url = reverse_lazy('anamnese-geral-list')

    def form_valid(self, form):
        messages.success(self.request, 'Anamnese Geral criada com sucesso!')
        return super().form_valid(form)


class AnamneseGeralUpdateView(LoginRequiredMixin, UpdateView):
    model = AnamneseGeral
    form_class = AnamneseGeralForm
    template_name = 'forms/anamnese_geral_form.html'
    success_url = reverse_lazy('anamnese-geral-list')

    def form_valid(self, form):
        messages.success(self.request, 'Anamnese Geral atualizada com sucesso!')
        return super().form_valid(form)


class AnamneseGeralDeleteView(LoginRequiredMixin, DeleteView):
    model = AnamneseGeral
    template_name = 'forms/anamnese_geral_confirm_delete.html'
    success_url = reverse_lazy('anamnese-geral-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Anamnese Geral deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# AnamneseAcupuntura Views
class AnamneseAcupunturaListView(LoginRequiredMixin, ListView):
    model = AnamneseAcupuntura
    template_name = 'forms/anamnese_acupuntura_list.html'
    context_object_name = 'fichas'
    paginate_by = 10


class AnamneseAcupunturaDetailView(LoginRequiredMixin, DetailView):
    model = AnamneseAcupuntura
    template_name = 'forms/anamnese_acupuntura_detail.html'
    context_object_name = 'ficha'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        from django.contrib.contenttypes.models import ContentType
        from .models import FollowUpSession
        ct = ContentType.objects.get_for_model(obj)
        context['sessions'] = FollowUpSession.objects.filter(content_type=ct, object_id=obj.pk).order_by('session_date')
        context['model_slug'] = 'anamnese-acupuntura'
        return context


class AnamneseAcupunturaCreateView(LoginRequiredMixin, CreateView):
    model = AnamneseAcupuntura
    form_class = AnamneseAcupunturaForm
    template_name = 'forms/anamnese_acupuntura_form.html'
    success_url = reverse_lazy('anamnese-acupuntura-list')

    def form_valid(self, form):
        messages.success(self.request, 'Anamnese - Acupuntura criada com sucesso!')
        return super().form_valid(form)


class AnamneseAcupunturaUpdateView(LoginRequiredMixin, UpdateView):
    model = AnamneseAcupuntura
    form_class = AnamneseAcupunturaForm
    template_name = 'forms/anamnese_acupuntura_form.html'
    success_url = reverse_lazy('anamnese-acupuntura-list')

    def form_valid(self, form):
        messages.success(self.request, 'Anamnese - Acupuntura atualizada com sucesso!')
        return super().form_valid(form)


class AnamneseAcupunturaDeleteView(LoginRequiredMixin, DeleteView):
    model = AnamneseAcupuntura
    template_name = 'forms/anamnese_acupuntura_confirm_delete.html'
    success_url = reverse_lazy('anamnese-acupuntura-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Anamnese - Acupuntura deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# FichaDrenagem Views
class FichaDrenagemListView(LoginRequiredMixin, ListView):
    model = FichaDrenagem
    template_name = 'forms/drenagem_list.html'
    context_object_name = 'fichas'
    paginate_by = 10


class FichaDrenagemDetailView(LoginRequiredMixin, DetailView):
    model = FichaDrenagem
    template_name = 'forms/drenagem_detail.html'
    context_object_name = 'ficha'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        from django.contrib.contenttypes.models import ContentType
        from .models import FollowUpSession
        ct = ContentType.objects.get_for_model(obj)
        context['sessions'] = FollowUpSession.objects.filter(content_type=ct, object_id=obj.pk).order_by('session_date')
        context['model_slug'] = 'drenagem'
        return context


class FichaDrenagemCreateView(LoginRequiredMixin, CreateView):
    model = FichaDrenagem
    form_class = FichaDrenagemForm
    template_name = 'forms/drenagem_form.html'
    success_url = reverse_lazy('drenagem-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Drenagem criada com sucesso!')
        return super().form_valid(form)


class FichaDrenagemUpdateView(LoginRequiredMixin, UpdateView):
    model = FichaDrenagem
    form_class = FichaDrenagemForm
    template_name = 'forms/drenagem_form.html'
    success_url = reverse_lazy('drenagem-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Drenagem atualizada com sucesso!')
        return super().form_valid(form)


class FichaDrenagemDeleteView(LoginRequiredMixin, DeleteView):
    model = FichaDrenagem
    template_name = 'forms/drenagem_confirm_delete.html'
    success_url = reverse_lazy('drenagem-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Ficha de Drenagem deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# FichaExercicios Views
class FichaExerciciosListView(LoginRequiredMixin, ListView):
    model = FichaExercicios
    template_name = 'forms/exercicios_list.html'
    context_object_name = 'fichas'
    paginate_by = 10


class FichaExerciciosDetailView(LoginRequiredMixin, DetailView):
    model = FichaExercicios
    template_name = 'forms/exercicios_detail.html'
    context_object_name = 'ficha'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        from django.contrib.contenttypes.models import ContentType
        from .models import FollowUpSession
        ct = ContentType.objects.get_for_model(obj)
        context['sessions'] = FollowUpSession.objects.filter(content_type=ct, object_id=obj.pk).order_by('session_date')
        context['model_slug'] = 'exercicios'
        return context


class FichaExerciciosCreateView(LoginRequiredMixin, CreateView):
    model = FichaExercicios
    form_class = FichaExerciciosForm
    template_name = 'forms/exercicios_form.html'
    success_url = reverse_lazy('exercicios-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Exercícios criada com sucesso!')
        return super().form_valid(form)


class FichaExerciciosUpdateView(LoginRequiredMixin, UpdateView):
    model = FichaExercicios
    form_class = FichaExerciciosForm
    template_name = 'forms/exercicios_form.html'
    success_url = reverse_lazy('exercicios-list')

    def form_valid(self, form):
        messages.success(self.request, 'Ficha de Exercícios atualizada com sucesso!')
        return super().form_valid(form)


class FichaExerciciosDeleteView(LoginRequiredMixin, DeleteView):
    model = FichaExercicios
    template_name = 'forms/exercicios_confirm_delete.html'
    success_url = reverse_lazy('exercicios-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Ficha de Exercícios deletada com sucesso!')
        return super().delete(request, *args, **kwargs)

# Toggle Concluido Views
@login_required

# all toggle endpoints require login
def toggle_anamnese_geral_concluido(request, pk):
    """Mark/unmark AnamneseGeral as concluída"""
    ficha = get_object_or_404(AnamneseGeral, pk=pk)
    ficha.concluido = not ficha.concluido
    ficha.save()
    status = 'marcada como concluída' if ficha.concluido else 'marcada como pendente'
    messages.success(request, f'Anamnese Geral {status}!')
    return redirect('anamnese-geral-detail', pk=pk)


@login_required
def toggle_anamnese_acupuntura_concluido(request, pk):
    """Mark/unmark AnamneseAcupuntura as concluída"""
    ficha = get_object_or_404(AnamneseAcupuntura, pk=pk)
    ficha.concluido = not ficha.concluido
    ficha.save()
    status = 'marcada como concluída' if ficha.concluido else 'marcada como pendente'
    messages.success(request, f'Anamnese - Acupuntura {status}!')
    return redirect('anamnese-acupuntura-detail', pk=pk)


@login_required
def toggle_drenagem_concluido(request, pk):
    """Mark/unmark FichaDrenagem as concluída"""
    ficha = get_object_or_404(FichaDrenagem, pk=pk)
    ficha.concluido = not ficha.concluido
    ficha.save()
    status = 'marcada como concluída' if ficha.concluido else 'marcada como pendente'
    messages.success(request, f'Ficha de Drenagem {status}!')
    return redirect('drenagem-detail', pk=pk)


@login_required
def toggle_exercicios_concluido(request, pk):
    """Mark/unmark FichaExercicios as concluída"""
    ficha = get_object_or_404(FichaExercicios, pk=pk)
    ficha.concluido = not ficha.concluido
    ficha.save()
    status = 'marcada como concluída' if ficha.concluido else 'marcada como pendente'
    messages.success(request, f'Ficha de Exercícios {status}!')
    return redirect('exercicios-detail', pk=pk)


@login_required

def add_followup(request, model_slug, pk):
    """Create a new FollowUpSession for a given procedure instance."""
    from django.contrib.contenttypes.models import ContentType
    from .models import FollowUpSession
    # map slug to model class
    slug_map = {
        'anamnese-geral': AnamneseGeral,
        'anamnese-acupuntura': AnamneseAcupuntura,
        'drenagem': FichaDrenagem,
        'exercicios': FichaExercicios,
    }
    model = slug_map.get(model_slug)
    if not model:
        messages.error(request, 'Procedimento inválido.')
        return redirect('index')
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        session_date = request.POST.get('session_date')
        notes = request.POST.get('notes', '')
        if session_date:
            # create session
            FollowUpSession.objects.create(
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.pk,
                session_date=session_date,
                notes=notes
            )
            messages.success(request, 'Sessão adicionada com sucesso!')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    return redirect(obj.pk)


@login_required

def edit_followup(request, session_id):
    from .models import FollowUpSession
    session = get_object_or_404(FollowUpSession, pk=session_id)
    if request.method == 'POST':
        if 'session_date' in request.POST:
            session.session_date = request.POST.get('session_date')
        session.notes = request.POST.get('notes', '')
        session.save()
        messages.success(request, 'Sessão atualizada com sucesso!')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def calendar_events(request):
    """API endpoint to return calendar events as JSON"""
    events = build_calendar_events()
    return JsonResponse(events, safe=False)


class CalendarDashboardView(LoginRequiredMixin, TemplateView):
    """Calendar dashboard view"""
    template_name = 'dashboard/calendar.html'