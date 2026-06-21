from django.urls import path

from .views import SpreadsheetImportView


urlpatterns = [
    path("", SpreadsheetImportView.as_view(), name="spreadsheet-import"),
]

