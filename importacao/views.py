from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormView

from .forms import SpreadsheetImportForm
from .services import ImportOptions, import_uploaded_spreadsheet


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class SpreadsheetImportView(StaffOnlyMixin, FormView):
    form_class = SpreadsheetImportForm
    template_name = "importacao/spreadsheet_import.html"

    def form_valid(self, form):
        options = ImportOptions(
            target=form.cleaned_data["target"],
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

        has_errors = any(item["result"].has_errors for item in results)
        saved_count = sum(1 for item in results if item["result"].saved)
        if options.dry_run:
            if has_errors:
                messages.warning(self.request, "A simulacao encontrou ajustes pendentes.")
            else:
                messages.info(self.request, "Simulacao concluida.")
        elif has_errors and saved_count:
            messages.warning(self.request, "Importacao concluida parcialmente.")
        elif has_errors:
            messages.error(self.request, "Nenhum registro foi salvo.")
        elif saved_count:
            messages.success(self.request, "Importacao concluida.")
        else:
            messages.info(self.request, "Nenhuma alteracao foi salva.")

        return self.render_to_response(self.get_context_data(form=form, results=results))
