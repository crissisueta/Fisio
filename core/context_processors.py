from django.conf import settings


def feedback_settings(request):
    return {
        "feedback_tab_text": getattr(settings, "FEEDBACK_TAB_TEXT", "Reportar erro"),
    }
