from io import BytesIO
from zipfile import ZipFile
from xml.sax.saxutils import escape

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from exercicios.models import CategoriaExercicio, ExercicioCatalogo
from importacao.services import ImportOptions, import_rows
from importacao.spreadsheets import read_spreadsheet
from pacientes.models import Paciente


class ImportacaoServiceTests(TestCase):
    def test_patient_import_creates_records(self):
        rows = [
            {
                "Nome Completo": "Ana Lima",
                "CPF": "111.222.333-44",
                "E-mail": "ana@example.com",
                "Profissao": "Professora",
                "Endereco": "Rua A, 10",
                "Bairro": "Centro",
                "CEP": "40000-000",
                "Telefone": "7133333333",
                "Celular": "71999999999",
                "Telefone Comercial": "",
                "Data Nascimento": "01/02/1990",
                "Data Matricula": "10/03/2026",
                "Plano": "Particular",
                "Observacoes": "Primeira importacao",
            }
        ]

        result = import_rows(rows, ImportOptions(target="pacientes", dry_run=False))

        self.assertTrue(result.saved)
        self.assertEqual(result.created_count, 1)
        paciente = Paciente.objects.get(cpf="111.222.333-44")
        self.assertEqual(paciente.nome, "Ana Lima")
        self.assertEqual(paciente.data_nascimento.isoformat(), "1990-02-01")

    def test_dry_run_does_not_create_records(self):
        rows = [
            {
                "nome": "Ana Lima",
                "cpf": "111.222.333-44",
                "email": "ana@example.com",
                "endereco": "Rua A, 10",
                "bairro": "Centro",
                "cep": "40000-000",
                "celular": "71999999999",
                "data_nascimento": "01/02/1990",
                "data_matricula": "10/03/2026",
                "plano": "Particular",
            }
        ]

        result = import_rows(rows, ImportOptions(target="pacientes", dry_run=True))

        self.assertFalse(result.saved)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.created_count, 1)
        self.assertFalse(Paciente.objects.exists())

    def test_real_import_with_errors_writes_nothing(self):
        rows = [
            {
                "nome": "Ana Lima",
                "cpf": "111.222.333-44",
                "endereco": "Rua A, 10",
                "bairro": "Centro",
                "cep": "40000-000",
                "celular": "71999999999",
                "data_nascimento": "01/02/1990",
                "data_matricula": "10/03/2026",
                "plano": "Particular",
            }
        ]

        result = import_rows(rows, ImportOptions(target="pacientes", dry_run=False))

        self.assertFalse(result.saved)
        self.assertTrue(result.has_errors)
        self.assertFalse(Paciente.objects.exists())

    def test_exercise_import_can_create_related_category(self):
        rows = [
            {
                "nome": "Ponte pelvica",
                "categoria": "Fortalecimento",
                "descricao": "Exercicio base",
                "ativo": "sim",
            }
        ]

        result = import_rows(
            rows,
            ImportOptions(target="exercicios", dry_run=False, create_related=True),
        )

        self.assertTrue(result.saved)
        self.assertTrue(CategoriaExercicio.objects.filter(nome="Fortalecimento").exists())
        self.assertTrue(ExercicioCatalogo.objects.filter(nome="Ponte pelvica").exists())


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ImportacaoViewTests(TestCase):
    def test_import_page_is_staff_only(self):
        user = User.objects.create_user(username="regular", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("spreadsheet-import"))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_import_csv(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        csv_content = (
            "nome,cpf,email,endereco,bairro,cep,celular,data_nascimento,data_matricula,plano\n"
            "Ana Lima,111.222.333-44,ana@example.com,\"Rua A, 10\",Centro,40000-000,71999999999,01/02/1990,10/03/2026,Particular\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile("pacientes.csv", csv_content, content_type="text/csv")

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "target": "pacientes",
                "arquivo": upload,
                "update_existing": "on",
                "create_related": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Paciente.objects.filter(cpf="111.222.333-44").exists())


class SpreadsheetReaderTests(TestCase):
    def test_reads_basic_xlsx_without_optional_dependency(self):
        upload = SimpleUploadedFile(
            "pacientes.xlsx",
            _build_xlsx(
                [
                    ["nome", "cpf", "email"],
                    ["Ana Lima", "111.222.333-44", "ana@example.com"],
                ]
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_spreadsheet(upload)

        self.assertEqual(data.sheet_name, "Pacientes")
        self.assertEqual(data.headers, ["nome", "cpf", "email"])
        self.assertEqual(data.rows[0]["nome"], "Ana Lima")


def _build_xlsx(rows):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Pacientes" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows))
    return buffer.getvalue()


def _worksheet_xml(rows):
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(row_xml)}
  </sheetData>
</worksheet>"""


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
