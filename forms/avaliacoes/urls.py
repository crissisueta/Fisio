from django.urls import path

from .views import (
    AvaliacaoCreateView,
    AvaliacaoDeleteView,
    AvaliacaoDetailView,
    AvaliacaoListView,
    AvaliacaoUpdateView,
)


urlpatterns = [
    path("avaliacoes/", AvaliacaoListView.as_view(), name="avaliacao-list"),
    path("avaliacoes/nova/", AvaliacaoCreateView.as_view(), name="avaliacao-create"),
    path("avaliacoes/<int:pk>/", AvaliacaoDetailView.as_view(), name="avaliacao-detail"),
    path("avaliacoes/<int:pk>/editar/", AvaliacaoUpdateView.as_view(), name="avaliacao-update"),
    path("avaliacoes/<int:pk>/deletar/", AvaliacaoDeleteView.as_view(), name="avaliacao-delete"),
]

