from .models import CategoriaExercicio, ExercicioCatalogo


def categoria_exercicio_list_queryset(request):
    queryset = CategoriaExercicio.all_objects.order_by("nome")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativas")

    if search:
        queryset = queryset.filter(nome__icontains=search)
    if status == "ativas":
        queryset = queryset.filter(is_active=True)
    elif status == "inativas":
        queryset = queryset.filter(is_active=False)

    return queryset


def exercicio_catalogo_list_queryset(request):
    queryset = ExercicioCatalogo.all_objects.select_related("categoria").order_by("nome")
    search = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    status = request.GET.get("status", "ativos")

    if search:
        queryset = queryset.filter(nome__icontains=search)
    if categoria_id:
        queryset = queryset.filter(categoria_id=categoria_id)
    if status == "ativos":
        queryset = queryset.filter(is_active=True)
    elif status == "inativos":
        queryset = queryset.filter(is_active=False)

    return queryset


def categorias_disponiveis_queryset():
    return CategoriaExercicio.objects.order_by("nome")

