from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    # FichaInscricao
    FichaInscricaoListView, FichaInscricaoDetailView, FichaInscricaoCreateView,
    FichaInscricaoUpdateView, FichaInscricaoDeleteView,
    # AnamneseGeral
    AnamneseGeralListView, AnamneseGeralDetailView, AnamneseGeralCreateView,
    AnamneseGeralUpdateView, AnamneseGeralDeleteView, toggle_anamnese_geral_concluido,
    # AnamneseAcupuntura
    AnamneseAcupunturaListView, AnamneseAcupunturaDetailView, AnamneseAcupunturaCreateView,
    AnamneseAcupunturaUpdateView, AnamneseAcupunturaDeleteView, toggle_anamnese_acupuntura_concluido,
    # FichaDrenagem
    FichaDrenagemListView, FichaDrenagemDetailView, FichaDrenagemCreateView,
    FichaDrenagemUpdateView, FichaDrenagemDeleteView, toggle_drenagem_concluido,
    # FichaExercicios
    FichaExerciciosListView, FichaExerciciosDetailView, FichaExerciciosCreateView,
    FichaExerciciosUpdateView, FichaExerciciosDeleteView, toggle_exercicios_concluido,
    # API
    get_paciente_data,
)

urlpatterns = [
    # API endpoints
    path('api/paciente/<int:paciente_id>/', get_paciente_data, name='api-paciente-data'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # FichaInscricao URLs
    path('inscricao/', FichaInscricaoListView.as_view(), name='inscricao-list'),
    path('inscricao/nova/', FichaInscricaoCreateView.as_view(), name='inscricao-create'),
    path('inscricao/<int:pk>/', FichaInscricaoDetailView.as_view(), name='inscricao-detail'),
    path('inscricao/<int:pk>/editar/', FichaInscricaoUpdateView.as_view(), name='inscricao-update'),
    path('inscricao/<int:pk>/deletar/', FichaInscricaoDeleteView.as_view(), name='inscricao-delete'),
    
    # AnamneseGeral URLs
    path('anamnese-geral/', AnamneseGeralListView.as_view(), name='anamnese-geral-list'),
    path('anamnese-geral/nova/', AnamneseGeralCreateView.as_view(), name='anamnese-geral-create'),
    path('anamnese-geral/<int:pk>/', AnamneseGeralDetailView.as_view(), name='anamnese-geral-detail'),
    path('anamnese-geral/<int:pk>/editar/', AnamneseGeralUpdateView.as_view(), name='anamnese-geral-update'),
    path('anamnese-geral/<int:pk>/deletar/', AnamneseGeralDeleteView.as_view(), name='anamnese-geral-delete'),
    
    # AnamneseAcupuntura URLs
    path('anamnese-acupuntura/', AnamneseAcupunturaListView.as_view(), name='anamnese-acupuntura-list'),
    path('anamnese-acupuntura/nova/', AnamneseAcupunturaCreateView.as_view(), name='anamnese-acupuntura-create'),
    path('anamnese-acupuntura/<int:pk>/', AnamneseAcupunturaDetailView.as_view(), name='anamnese-acupuntura-detail'),
    path('anamnese-acupuntura/<int:pk>/editar/', AnamneseAcupunturaUpdateView.as_view(), name='anamnese-acupuntura-update'),
    path('anamnese-acupuntura/<int:pk>/deletar/', AnamneseAcupunturaDeleteView.as_view(), name='anamnese-acupuntura-delete'),
    
    # FichaDrenagem URLs
    path('drenagem/', FichaDrenagemListView.as_view(), name='drenagem-list'),
    path('drenagem/nova/', FichaDrenagemCreateView.as_view(), name='drenagem-create'),
    path('drenagem/<int:pk>/', FichaDrenagemDetailView.as_view(), name='drenagem-detail'),
    path('drenagem/<int:pk>/editar/', FichaDrenagemUpdateView.as_view(), name='drenagem-update'),
    path('drenagem/<int:pk>/deletar/', FichaDrenagemDeleteView.as_view(), name='drenagem-delete'),
    
    # FichaExercicios URLs
    path('exercicios/', FichaExerciciosListView.as_view(), name='exercicios-list'),
    path('exercicios/novo/', FichaExerciciosCreateView.as_view(), name='exercicios-create'),
    path('exercicios/<int:pk>/', FichaExerciciosDetailView.as_view(), name='exercicios-detail'),
    path('exercicios/<int:pk>/editar/', FichaExerciciosUpdateView.as_view(), name='exercicios-update'),
    path('exercicios/<int:pk>/deletar/', FichaExerciciosDeleteView.as_view(), name='exercicios-delete'),
    path('exercicios/<int:pk>/concluido/', toggle_exercicios_concluido, name='exercicios-toggle-concluido'),
    
    # Toggle Concluido URLs
    path('anamnese-geral/<int:pk>/concluido/', toggle_anamnese_geral_concluido, name='anamnese-geral-toggle-concluido'),
    path('anamnese-acupuntura/<int:pk>/concluido/', toggle_anamnese_acupuntura_concluido, name='anamnese-acupuntura-toggle-concluido'),
    path('drenagem/<int:pk>/concluido/', toggle_drenagem_concluido, name='drenagem-toggle-concluido'),
]
