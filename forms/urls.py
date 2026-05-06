from .avaliacoes.urls import urlpatterns as avaliacoes_urlpatterns
from .exercicios.urls import urlpatterns as exercicios_urlpatterns
from .pacientes.urls import urlpatterns as pacientes_urlpatterns
from .procedimentos.urls import urlpatterns as procedimentos_urlpatterns


urlpatterns = [
    *pacientes_urlpatterns,
    *avaliacoes_urlpatterns,
    *procedimentos_urlpatterns,
    *exercicios_urlpatterns,
]
