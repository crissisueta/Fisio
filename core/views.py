import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FeedbackForm


logger = logging.getLogger(__name__)


def _source_page_url(request, source_page):
    if source_page:
        return source_page
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return referer
    return request.build_absolute_uri(request.get_full_path())


def _feedback_body(request, form):
    user = request.user
    cleaned_data = form.cleaned_data
    source_page = _source_page_url(request, cleaned_data["source_page"])
    timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S %Z")

    type_labels = dict(FeedbackForm.TYPE_CHOICES)
    feedback_type = type_labels.get(cleaned_data.get("feedback_type"), "Feedback")

    lines = [
        f"Tipo: {feedback_type}",
        f"Pagina: {source_page}",
        f"Enviado em: {timestamp}",
        "",
        "Mensagem:",
        cleaned_data["message"],
    ]

    if getattr(settings, "FEEDBACK_INCLUDE_METADATA", True):
        lines.extend(
            [
                "",
                "Metadados:",
                f"Usuario: {user.get_username()}",
                f"ID do usuario: {user.pk}",
                f"Email do usuario: {user.email or '-'}",
                f"Metodo: {request.method}",
                f"IP: {request.META.get('REMOTE_ADDR', '-')}",
                f"User-Agent: {request.META.get('HTTP_USER_AGENT', '-')}",
            ]
        )

    return "\n".join(lines), feedback_type


@login_required
@require_POST
def submit_feedback(request):
    form = FeedbackForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "ok": False,
                "message": "Confira a mensagem e tente novamente.",
                "errors": form.errors,
            },
            status=400,
        )

    recipient = getattr(settings, "FEEDBACK_EMAIL_TO", "")
    if not recipient:
        return JsonResponse(
            {"ok": False, "message": "Envio de feedback nao configurado."},
            status=503,
        )

    body, feedback_type = _feedback_body(request, form)
    subject_prefix = getattr(settings, "FEEDBACK_EMAIL_SUBJECT_PREFIX", "[Fisio Feedback]")
    subject = f"{subject_prefix} {feedback_type}"

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send feedback email.")
        return JsonResponse(
            {"ok": False, "message": "Nao foi possivel enviar agora. Tente novamente."},
            status=502,
        )

    return JsonResponse({"ok": True, "message": "Obrigado. Feedback enviado."})
