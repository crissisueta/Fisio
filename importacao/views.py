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
        result = import_uploaded_spreadsheet(
            form.cleaned_data["arquivo"],
            options,
            sheet_name=form.cleaned_data["sheet_name"],
        )

        if result.saved:
            messages.success(self.request, "Importacao concluida.")
        elif result.has_errors and not result.dry_run:
            messages.error(self.request, "Nenhum registro foi salvo.")
        elif result.has_errors:
            messages.warning(self.request, "A simulacao encontrou ajustes pendentes.")
        else:
            messages.info(self.request, "Simulacao concluida.")

        return self.render_to_response(self.get_context_data(form=form, result=result))

