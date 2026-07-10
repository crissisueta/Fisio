from datetime import date, datetime, time
from io import BytesIO
from zipfile import ZipFile
from xml.sax.saxutils import escape

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from exercicios.models import CategoriaExercicio, ExercicioCatalogo, ProcedimentoExercicio, SessaoExercicio
from importacao.services import ImportOptions, import_rows, import_uploaded_spreadsheet
from importacao.spreadsheets import read_exercise_tracking_spreadsheet, read_spreadsheet
from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao, TipoProcedimento


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

    def test_exercise_tracking_import_creates_sessions_and_marks(self):
        performed_date = date(2026, 5, 8)
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "MAI26": [
                        ["", "Ana Lima"],
                        ["", "", "", _excel_serial(performed_date)],
                        ["", "Estabilizadores", "BOLA", "AMAR"],
                        ["", "EXERCICIOS DE SOLO"],
                        ["", "Exercicios de Solo", "Ponte", "X"],
                        ["", "Exercicios de Solo", "Ponte", "X/"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        result = import_uploaded_spreadsheet(
            upload,
            ImportOptions(target="historico_exercicios", dry_run=False),
        )

        self.assertTrue(result.saved)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.created_count, 2)
        self.assertEqual(result.skipped_count, 1)
        paciente = Paciente.objects.get(nome="Ana Lima")
        self.assertIsNone(paciente.cpf)
        self.assertTrue(paciente.profile_incomplete)
        tipo = TipoProcedimento.objects.get(nome="Pilates")
        procedimento = Procedimento.objects.get(paciente=paciente, tipo_procedimento=tipo)
        sessao = Sessao.objects.get(procedimento=procedimento)
        self.assertEqual(sessao.data_hora.date(), performed_date)
        self.assertEqual(sessao.status, Sessao.STATUS_REALIZADA)
        self.assertEqual(ProcedimentoExercicio.objects.filter(procedimento=procedimento).count(), 2)
        self.assertEqual(SessaoExercicio.objects.filter(sessao=sessao).count(), 2)
        self.assertTrue(ExercicioCatalogo.objects.filter(nome="BOLA", categoria__nome="Estabilizadores").exists())


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

    def test_staff_can_import_multiple_csv_files(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        first_upload = SimpleUploadedFile(
            "pacientes-1.csv",
            (
                "nome,cpf,email,endereco,bairro,cep,celular,data_nascimento,data_matricula,plano\n"
                "Ana Lima,111.222.333-44,ana@example.com,\"Rua A, 10\",Centro,40000-000,71999999999,01/02/1990,10/03/2026,Particular\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        second_upload = SimpleUploadedFile(
            "pacientes-2.csv",
            (
                "nome,cpf,email,endereco,bairro,cep,celular,data_nascimento,data_matricula,plano\n"
                "Bia Souza,222.333.444-55,bia@example.com,\"Rua B, 20\",Centro,40000-001,71888888888,05/06/1985,11/03/2026,Particular\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "target": "pacientes",
                "arquivo": [first_upload, second_upload],
                "update_existing": "on",
                "create_related": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Paciente.objects.filter(cpf="111.222.333-44").exists())
        self.assertTrue(Paciente.objects.filter(cpf="222.333.444-55").exists())
        self.assertContains(response, "pacientes-1.csv")
        self.assertContains(response, "pacientes-2.csv")

    def test_patient_detail_shows_incomplete_profile_reminder(self):
        user = User.objects.create_user(username="staff", password="testpass123")
        paciente = Paciente.objects.create(nome="Ana Lima")
        self.client.force_login(user)

        response = self.client.get(reverse("inscricao-detail", args=[paciente.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro do paciente incompleto.")
        self.assertContains(response, "Completar cadastro")


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

    def test_reads_exercise_tracking_xlsx_across_tabs(self):
        first_date = date(2026, 5, 8)
        second_date = date(2026, 6, 1)
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "MAI26": [
                        ["", "Ana Lima"],
                        ["", "OBSERVACOES:", "", "Paciente relatou dor leve."],
                        ["", "", "", _excel_serial(first_date)],
                        ["", "Estabilizadores", "BOLA", "AMAR"],
                        ["", "EXERCICIOS DE SOLO"],
                        ["", "Exercicios de Solo", "Ponte", "X"],
                    ],
                    "JUN26": [
                        ["", "Ana Lima"],
                        ["", "", "", _excel_serial(second_date)],
                        ["", "Estabilizadores", "ROLO", "X/"],
                    ],
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_exercise_tracking_spreadsheet(upload)

        self.assertEqual(data.sheet_name, "Todas as abas")
        self.assertEqual(len(data.rows), 3)
        self.assertEqual(data.rows[0]["paciente_nome"], "Ana Lima")
        self.assertEqual(data.rows[0]["data"], first_date)
        self.assertEqual(data.rows[0]["categoria"], "Estabilizadores")
        self.assertEqual(data.rows[0]["exercicio"], "BOLA")
        self.assertEqual(data.rows[0]["marca"], "AMAR")
        self.assertEqual(data.rows[2]["sheet_name"], "JUN26")


def _build_xlsx(rows):
    return _build_xlsx_workbook({"Pacientes": rows})


def _build_xlsx_workbook(sheets):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        content_type_overrides = "\n".join(
            f'  <Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index, _name in enumerate(sheets, start=1)
        )
        archive.writestr(
            "[Content_Types].xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{content_type_overrides}
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        workbook_sheets = "\n".join(
            f'    <sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, name in enumerate(sheets, start=1)
        )
        archive.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
{workbook_sheets}
  </sheets>
</workbook>""",
        )
        workbook_rels = "\n".join(
            f'  <Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index, _name in enumerate(sheets, start=1)
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{workbook_rels}
</Relationships>""",
        )
        for index, rows in enumerate(sheets.values(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))
    return buffer.getvalue()


def _worksheet_xml(rows):
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            if value == "" or value is None:
                continue
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(_cell_xml(reference, value))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(row_xml)}
  </sheetData>
</worksheet>"""


def _cell_xml(reference, value):
    if isinstance(value, (int, float)):
        return f'<c r="{reference}"><v>{value}</v></c>'
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _excel_serial(value):
    return (datetime.combine(value, time.min) - datetime(1899, 12, 30)).days


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
