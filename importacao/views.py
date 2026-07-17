from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic.edit import FormView

from core.models import ActivityLog
from core.services.activity import log_activity
from .forms import SpreadsheetImportForm
from .services import ImportOptions, TARGET_EXERCISE_TRACKING, import_uploaded_spreadsheet


SESSION_RESULTS_KEY = "spreadsheet_import_results"


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class SpreadsheetImportView(StaffOnlyMixin, FormView):
    form_class = SpreadsheetImportForm
    template_name = "importacao/spreadsheet_import.html"

    def get_success_url(self):
        return self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["results"] = self.request.session.pop(SESSION_RESULTS_KEY, None)
        return context

    def form_valid(self, form):
        options = ImportOptions(
            target=TARGET_EXERCISE_TRACKING,
            update_existing=form.cleaned_data["update_existing"],
            create_related=form.cleaned_data["create_related"],
            dry_run=form.cleaned_data["dry_run"],
        )
        results = [
            {
                "filename": arquivo.name,
                "result": import_uploaded_spreadsheet(
                    arquivo,
                    options,
                    sheet_name=form.cleaned_data["sheet_name"],
                ),
            }
            for arquivo in form.cleaned_data["arquivo"]
        ]
        self.request.session[SESSION_RESULTS_KEY] = _serialize_import_results(results)
        _add_import_messages(self.request, options, results)
        _log_import_activity(self.request.user, options, results)
        return redirect(self.get_success_url())


def _serialize_import_results(results):
    serialized = []
    for item in results:
        result = item["result"]
        serialized.append(
            {
                "filename": item["filename"],
                "result": {
                    "target": result.target,
                    "sheet_name": result.sheet_name,
                    "dry_run": result.dry_run,
                    "saved": result.saved,
                    "errors": result.errors,
                    "created_count": result.created_count,
                    "updated_count": result.updated_count,
                    "skipped_count": result.skipped_count,
                    "category_count": result.category_count,
                    "exercise_count": result.exercise_count,
                    "mark_count": result.mark_count,
                    "rows": [
                        {
                            "row_number": row.row_number,
                            "action": row.action,
                            "status": row.status,
                            "values": row.values,
                            "errors": row.errors,
                        }
                        for row in result.rows
                    ],
                },
            }
        )
    return serialized


def _add_import_messages(request, options: ImportOptions, results) -> None:
    has_errors = any(item["result"].has_errors for item in results)
    saved_count = sum(1 for item in results if item["result"].saved)
    total_count = len(results)
    failed_count = sum(1 for item in results if item["result"].has_errors)

    if options.dry_run:
        if has_errors:
            messages.warning(request, "A simulacao encontrou ajustes pendentes.")
        else:
            messages.info(request, "Simulacao concluida.")
    elif has_errors:
        messages.error(
            request,
            f"Importacao com falha em {failed_count} de {total_count} arquivo(s). Verifique os detalhes antes de reenviar.",
        )
    elif saved_count:
        messages.success(request, "Importacao concluida.")
    else:
        messages.info(request, "Nenhuma alteracao foi salva.")


def _log_import_activity(user, options: ImportOptions, results) -> None:
    if not results:
        return

    total_count = len(results)
    failed_count = sum(1 for item in results if item["result"].has_errors)
    saved_count = sum(1 for item in results if item["result"].saved)
    created_count = sum(item["result"].created_count for item in results)
    updated_count = sum(item["result"].updated_count for item in results)
    mark_count = sum(item["result"].mark_count for item in results)

    metadata = {
        "target": options.target,
        "dry_run": options.dry_run,
        "file_count": total_count,
        "failed_count": failed_count,
        "saved_count": saved_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "mark_count": mark_count,
    }

    if failed_count:
        if total_count == 1:
            message = "teve falha ao importar uma planilha"
        else:
            message = f"teve falha ao importar {failed_count} de {total_count} planilhas"
        log_activity(
            user=user,
            event_type="spreadsheet_import.failed",
            message=message,
            level=ActivityLog.LEVEL_ERROR,
            metadata=metadata,
        )
        return

    if options.dry_run:
        log_activity(
            user=user,
            event_type="spreadsheet_import.simulated",
            message=f"simulou a importação de {_pluralize(total_count, 'planilha', 'planilhas')}",
            level=ActivityLog.LEVEL_INFO,
            metadata=metadata,
        )
        return

    if saved_count:
        log_activity(
            user=user,
            event_type="spreadsheet_import.success",
            message=f"importou {_pluralize(saved_count, 'planilha', 'planilhas')}",
            level=ActivityLog.LEVEL_SUCCESS,
            metadata=metadata,
        )
        return

    log_activity(
        user=user,
        event_type="spreadsheet_import.no_changes",
        message="concluiu uma importação sem alterações",
        level=ActivityLog.LEVEL_INFO,
        metadata=metadata,
    )


def _pluralize(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"
