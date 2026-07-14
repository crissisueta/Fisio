import json
import re
import unicodedata
from datetime import date, datetime, time
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile
from xml.sax.saxutils import escape

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
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

        with patch("importacao.services.resequence_sessoes") as resequence_sessoes_mock:
            result = import_uploaded_spreadsheet(
                upload,
                ImportOptions(target="historico_exercicios", dry_run=False),
            )

        self.assertTrue(result.saved)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.mark_count, 3)
        self.assertEqual(resequence_sessoes_mock.call_count, 1)
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

    def test_import_page_has_submit_guard_script(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("spreadsheet-import"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-import-submit")
        self.assertContains(response, "Importando...")
        self.assertContains(response, "submit.disabled = true")

    def test_import_page_only_shows_exercise_history_import(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("spreadsheet-import"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Importar Histórico de Exercícios")
        self.assertContains(response, "Lotes maiores devem ser processados pelo comando em lote")
        self.assertNotContains(response, 'name="target"')
        self.assertNotContains(response, ".csv")

    def test_staff_imports_tracking_xlsx_without_target_field(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        upload = SimpleUploadedFile(
            "referencia-anonima.xlsx",
            _build_reference_tracking_xlsx(date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": upload,
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "referencia-anonima.xlsx")
        self.assertEqual(CategoriaExercicio.objects.count(), 7)
        self.assertEqual(ProcedimentoExercicio.objects.count(), 188)
        self.assertEqual(SessaoExercicio.objects.count(), 4)

    @override_settings(IMPORTACAO_WEB_MAX_FILES=10)
    def test_staff_can_import_multiple_tracking_xlsx_files(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        performed_date = date(2026, 7, 6)
        first_upload = SimpleUploadedFile(
            "historico-1.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Um"],
                        ["", "", "", _excel_serial(performed_date)],
                        ["", "Solo", "Ponte", "X"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        second_upload = SimpleUploadedFile(
            "historico-2.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Dois"],
                        ["", "", "", _excel_serial(performed_date)],
                        ["", "Solo", "Ponte", "X/"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": [first_upload, second_upload],
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "historico-1.xlsx")
        self.assertContains(response, "historico-2.xlsx")
        self.assertEqual(Paciente.objects.count(), 2)
        self.assertEqual(ExercicioCatalogo.objects.filter(nome="Ponte", categoria__nome="Solo").count(), 1)
        self.assertEqual(ProcedimentoExercicio.objects.count(), 2)
        self.assertEqual(SessaoExercicio.objects.count(), 2)

    @override_settings(IMPORTACAO_WEB_MAX_FILES=10)
    def test_multiple_upload_reports_success_and_failure_per_file(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        valid_upload = SimpleUploadedFile(
            "historico-valido.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Valido"],
                        ["", "", "", _excel_serial(date(2026, 7, 6))],
                        ["", "Solo", "Ponte", "X"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        invalid_upload = SimpleUploadedFile("historico-invalido.xlsx", b"nao e xlsx", content_type="application/octet-stream")

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": [valid_upload, invalid_upload],
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Paciente.objects.filter(nome="Paciente Valido").exists())
        self.assertContains(response, "historico-valido.xlsx")
        self.assertContains(response, "historico-invalido.xlsx")
        self.assertContains(response, "Arquivo XLSX inválido")
        self.assertContains(response, "Importacao com falha em 1 de 2 arquivo(s)")

    def test_web_import_rejects_batches_above_configured_limit(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        first_upload = SimpleUploadedFile(
            "historico-1.xlsx",
            _tracking_xlsx_for_patient("Paciente Um", date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        second_upload = SimpleUploadedFile(
            "historico-2.xlsx",
            _tracking_xlsx_for_patient("Paciente Dois", date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": [first_upload, second_upload],
                "update_existing": "on",
                "create_related": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A importacao web aceita no maximo 1 arquivo")
        self.assertFalse(Paciente.objects.exists())
        self.assertFalse(SessaoExercicio.objects.exists())

    def test_tracking_import_uses_post_redirect_get_and_refresh_does_not_repost(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        content = _build_reference_tracking_xlsx(date(2026, 7, 6))

        response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": SimpleUploadedFile(
                    "referencia-anonima.xlsx",
                    content,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                "update_existing": "on",
                "create_related": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        after_post_counts = _tracking_counts()
        self.assertEqual(after_post_counts["session_exercises"], 4)

        redirected = self.client.get(response["Location"])

        self.assertEqual(redirected.status_code, 200)
        self.assertContains(redirected, "referencia-anonima.xlsx")
        self.assertContains(redirected, "Importacao concluida")
        self.assertEqual(_tracking_counts(), after_post_counts)

        refreshed = self.client.get(response["Location"])

        self.assertEqual(refreshed.status_code, 200)
        self.assertNotContains(refreshed, "referencia-anonima.xlsx")
        self.assertEqual(_tracking_counts(), after_post_counts)

    def test_repeated_tracking_post_does_not_duplicate_database_state(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        content = _build_reference_tracking_xlsx(date(2026, 7, 6))

        first_response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": SimpleUploadedFile(
                    "referencia-anonima.xlsx",
                    content,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                "update_existing": "on",
                "create_related": "on",
            },
        )
        after_first_counts = _tracking_counts()
        second_response = self.client.post(
            reverse("spreadsheet-import"),
            {
                "arquivo": SimpleUploadedFile(
                    "referencia-anonima.xlsx",
                    content,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                "update_existing": "on",
                "create_related": "on",
            },
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(after_first_counts["procedure_exercises"], 188)
        self.assertEqual(after_first_counts["session_exercises"], 4)
        self.assertEqual(_tracking_counts(), after_first_counts)

    def test_patient_detail_shows_incomplete_profile_reminder(self):
        user = User.objects.create_user(username="staff", password="testpass123")
        paciente = Paciente.objects.create(nome="Ana Lima")
        self.client.force_login(user)

        response = self.client.get(reverse("inscricao-detail", args=[paciente.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro do paciente incompleto.")
        self.assertContains(response, "Completar cadastro")
        self.assertContains(response, 'data-bs-dismiss="alert"')
        self.assertContains(response, 'aria-label="Fechar"')


class ImportarHistoricosCommandTests(TestCase):
    def test_imports_single_file(self):
        with TemporaryDirectory() as tmpdir:
            path = _write_tracking_file(tmpdir, "historico-001.xlsx", "Paciente Comando")
            output = StringIO()

            call_command("importar_historicos", str(path), stdout=output)

        self.assertIn("Processados: 1", output.getvalue())
        self.assertIn("Concluidos: 1", output.getvalue())
        self.assertTrue(Paciente.objects.filter(nome="Paciente Comando").exists())
        self.assertEqual(SessaoExercicio.objects.count(), 1)

    def test_imports_directory_with_five_files(self):
        with TemporaryDirectory() as tmpdir:
            for index in range(5):
                _write_tracking_file(tmpdir, f"historico-{index:03d}.xlsx", f"Paciente Lote {index}")
            output = StringIO()

            call_command("importar_historicos", tmpdir, stdout=output)

        self.assertIn("Processados: 5", output.getvalue())
        self.assertEqual(Paciente.objects.count(), 5)
        self.assertEqual(SessaoExercicio.objects.count(), 5)

    def test_dry_run_does_not_change_database(self):
        with TemporaryDirectory() as tmpdir:
            path = _write_tracking_file(tmpdir, "historico-001.xlsx", "Paciente Dry Run")
            output = StringIO()

            call_command("importar_historicos", str(path), dry_run=True, stdout=output)

        self.assertIn("resultado: simulado", output.getvalue())
        self.assertEqual(_tracking_counts(), _empty_tracking_counts())

    def test_continue_on_error_processes_valid_files_after_invalid_file(self):
        with TemporaryDirectory() as tmpdir:
            _write_tracking_file(tmpdir, "001-valido.xlsx", "Paciente Valido Antes")
            Path(tmpdir, "002-invalido.xlsx").write_bytes(b"nao e xlsx")
            _write_tracking_file(tmpdir, "003-valido.xlsx", "Paciente Valido Depois")
            output = StringIO()

            with self.assertRaises(CommandError):
                call_command("importar_historicos", tmpdir, continue_on_error=True, stdout=output)

        self.assertIn("Continuando para o proximo arquivo", output.getvalue())
        self.assertIn("Falharam: 1", output.getvalue())
        self.assertTrue(Paciente.objects.filter(nome="Paciente Valido Antes").exists())
        self.assertTrue(Paciente.objects.filter(nome="Paciente Valido Depois").exists())

    def test_stops_on_first_error_without_continue_on_error(self):
        with TemporaryDirectory() as tmpdir:
            _write_tracking_file(tmpdir, "001-valido.xlsx", "Paciente Antes")
            Path(tmpdir, "002-invalido.xlsx").write_bytes(b"nao e xlsx")
            _write_tracking_file(tmpdir, "003-valido.xlsx", "Paciente Depois")
            output = StringIO()

            with self.assertRaises(CommandError):
                call_command("importar_historicos", tmpdir, stdout=output)

        self.assertIn("Processados: 2", output.getvalue())
        self.assertTrue(Paciente.objects.filter(nome="Paciente Antes").exists())
        self.assertFalse(Paciente.objects.filter(nome="Paciente Depois").exists())

    def test_writes_json_report(self):
        with TemporaryDirectory() as tmpdir:
            path = _write_tracking_file(tmpdir, "historico-001.xlsx", "Paciente Relatorio")
            report_path = Path(tmpdir, "relatorio.json")

            call_command("importar_historicos", str(path), dry_run=True, report=str(report_path), stdout=StringIO())

            data = json.loads(report_path.read_text())

        self.assertEqual(data[0]["arquivo"], "historico-001.xlsx")
        self.assertEqual(data[0]["status"], "simulado")
        self.assertIn("duracao", data[0])

    def test_failure_returns_command_error(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "invalido.xlsx")
            path.write_bytes(b"nao e xlsx")

            with self.assertRaises(CommandError):
                call_command("importar_historicos", str(path), stdout=StringIO())

    def test_reexecution_is_idempotent(self):
        with TemporaryDirectory() as tmpdir:
            path = _write_tracking_file(tmpdir, "historico-001.xlsx", "Paciente Idempotente")
            call_command("importar_historicos", str(path), stdout=StringIO())
            after_first = _tracking_counts()
            call_command("importar_historicos", str(path), stdout=StringIO())

        self.assertEqual(_tracking_counts(), after_first)
        self.assertEqual(SessaoExercicio.objects.count(), 1)

    def test_rolls_back_only_current_file_when_later_file_fails(self):
        from importacao import services as importacao_services

        original = importacao_services._get_or_create_tracking_session_exercise

        def fail_for_one_patient(sessao, *args, **kwargs):
            if sessao.procedimento.paciente.nome == "Paciente Falha":
                raise DatabaseError("falha simulada")
            return original(sessao, *args, **kwargs)

        with TemporaryDirectory() as tmpdir:
            _write_tracking_file(tmpdir, "001-ok.xlsx", "Paciente Ok")
            _write_tracking_file(tmpdir, "002-falha.xlsx", "Paciente Falha")
            _write_tracking_file(tmpdir, "003-depois.xlsx", "Paciente Depois")

            with patch("importacao.services._get_or_create_tracking_session_exercise", side_effect=fail_for_one_patient):
                with self.assertRaises(CommandError):
                    call_command("importar_historicos", tmpdir, continue_on_error=True, stdout=StringIO())

        self.assertTrue(Paciente.objects.filter(nome="Paciente Ok").exists())
        self.assertFalse(Paciente.objects.filter(nome="Paciente Falha").exists())
        self.assertTrue(Paciente.objects.filter(nome="Paciente Depois").exists())
        self.assertEqual(SessaoExercicio.objects.count(), 2)


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
        self.assertEqual(data.rows[0]["marcacoes"][0]["data"], first_date)
        self.assertEqual(data.rows[0]["categoria"], "Estabilizadores")
        self.assertEqual(data.rows[0]["exercicio"], "BOLA")
        self.assertEqual(data.rows[0]["marcacoes"][0]["marca"], "AMAR")
        self.assertEqual(data.rows[2]["sheet_name"], "JUN26")
        self.assertEqual(data.rows[2]["marcacoes"][0]["data"], second_date)

    def test_reads_vertical_merged_category_for_unmarked_exercises(self):
        performed_date = date(2026, 7, 6)
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(performed_date)],
                        ["", "Reformer", "Footwork", "X"],
                        ["", "", "Hundred", ""],
                        ["", "", "Short Spine", "X/"],
                    ]
                },
                merges={"JUL26": ["B3:B5"]},
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_exercise_tracking_spreadsheet(upload)

        self.assertEqual([row["categoria"] for row in data.rows], ["Reformer", "Reformer", "Reformer"])
        self.assertEqual([row["exercicio"] for row in data.rows], ["Footwork", "Hundred", "Short Spine"])
        self.assertEqual(data.rows[1]["marcacoes"], [])
        self.assertEqual(data.rows[2]["marcacoes"][0]["marca"], "X/")

    def test_reads_horizontal_merged_category_header_without_creating_exercise(self):
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(date(2026, 7, 6))],
                        ["", "Trapezio", ""],
                        ["", "Trapezio", "Tower", ""],
                    ]
                },
                merges={"JUL26": ["B3:C3"]},
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_exercise_tracking_spreadsheet(upload)

        self.assertEqual(len(data.rows), 1)
        self.assertEqual(data.rows[0]["categoria"], "Trapezio")
        self.assertEqual(data.rows[0]["exercicio"], "Tower")
        self.assertEqual(data.rows[0]["marcacoes"], [])

    def test_rejects_exercise_without_determined_category(self):
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(date(2026, 7, 6))],
                        ["", "", "Hundred", "X"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        result = import_uploaded_spreadsheet(
            upload,
            ImportOptions(target="historico_exercicios", dry_run=False),
        )

        self.assertFalse(result.saved)
        self.assertTrue(result.has_errors)
        self.assertIn("linha 3", result.errors[0])
        self.assertIn("Hundred", result.errors[0])

    def test_imports_unmarked_exercises_without_creating_fake_sessions(self):
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(date(2026, 7, 6))],
                        ["", "Cadeira", "Swan", ""],
                        ["", "Cadeira", "Push Down", "X"],
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
        paciente = Paciente.objects.get(nome="Paciente Teste")
        procedimento = Procedimento.objects.get(paciente=paciente, tipo_procedimento__nome="Pilates")
        self.assertEqual(ProcedimentoExercicio.objects.filter(procedimento=procedimento).count(), 2)
        self.assertEqual(Sessao.objects.filter(procedimento=procedimento).count(), 1)
        self.assertEqual(SessaoExercicio.objects.filter(sessao__procedimento=procedimento).count(), 1)
        self.assertTrue(ExercicioCatalogo.objects.filter(nome="Swan", categoria__nome="Cadeira").exists())

    def test_import_is_idempotent_for_reference_fixture(self):
        performed_date = date(2026, 7, 6)
        content = _build_reference_tracking_xlsx(performed_date)

        self.assertEqual(_tracking_counts(), _empty_tracking_counts())

        first_result = import_uploaded_spreadsheet(
            SimpleUploadedFile(
                "referencia-anonima.xlsx",
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ImportOptions(target="historico_exercicios", dry_run=False),
        )
        after_first_counts = _tracking_counts()
        second_result = import_uploaded_spreadsheet(
            SimpleUploadedFile(
                "referencia-anonima.xlsx",
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ImportOptions(target="historico_exercicios", dry_run=False),
        )

        self.assertTrue(first_result.saved)
        self.assertTrue(second_result.saved)
        self.assertEqual(first_result.created_count, 188)
        self.assertEqual(first_result.updated_count, 0)
        self.assertEqual(second_result.created_count, 0)
        self.assertEqual(second_result.updated_count, 188)
        self.assertEqual(first_result.category_count, 7)
        self.assertEqual(first_result.exercise_count, 188)
        self.assertEqual(first_result.mark_count, 4)
        self.assertEqual(second_result.category_count, 7)
        self.assertEqual(second_result.exercise_count, 188)
        self.assertEqual(second_result.mark_count, 4)
        self.assertEqual(CategoriaExercicio.objects.count(), 7)
        self.assertEqual(ExercicioCatalogo.objects.count(), 188)
        self.assertEqual(SessaoExercicio.objects.count(), 4)
        self.assertEqual(set(Sessao.objects.values_list("data_hora__date", flat=True)), {performed_date})
        self.assertFalse(ExercicioCatalogo.objects.filter(categoria__nome="Sem categoria").exists())
        self.assertEqual(_tracking_counts(), after_first_counts)

        false_headers = ["TRAPÉZIO", "CADEIRA COMBO", "BARRIL", "COREALIGN", "OBSERVAÇÕES"]
        self.assertFalse(ExercicioCatalogo.objects.filter(nome__in=false_headers).exists())
        self.assertFalse(SessaoExercicio.objects.filter(exercicio__nome__in=false_headers).exists())

        paciente = Paciente.objects.get(nome="Paciente Referencia")
        procedimento = Procedimento.objects.get(paciente=paciente, tipo_procedimento__nome="Pilates")
        self.assertEqual(ProcedimentoExercicio.objects.filter(procedimento=procedimento).count(), 188)

    def test_reference_tracking_import_query_regression(self):
        upload = SimpleUploadedFile(
            "referencia-anonima.xlsx",
            _build_reference_tracking_xlsx(date(2026, 7, 6)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        with CaptureQueriesContext(connection) as queries:
            result = import_uploaded_spreadsheet(
                upload,
                ImportOptions(target="historico_exercicios", dry_run=False),
            )

        self.assertTrue(result.saved)
        self.assertFalse(result.has_errors)
        self.assertLessEqual(len(queries.captured_queries), 450)
        self.assertFalse(
            any(
                "forms_sessaoexercicio" in query["sql"] and "LIMIT 1" in query["sql"]
                for query in queries.captured_queries
            )
        )

    def test_import_keeps_same_exercise_name_in_different_categories(self):
        performed_date = date(2026, 7, 6)
        content = _build_xlsx_workbook(
            {
                "JUL26": [
                    ["", "Paciente Repeticao"],
                    ["", "", "", _excel_serial(performed_date)],
                    ["", "Reformer", "Ponte", "X"],
                    ["", "Cadeira", "Ponte", ""],
                ]
            }
        )

        first_result = import_uploaded_spreadsheet(
            SimpleUploadedFile(
                "repetidos-anonimo.xlsx",
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ImportOptions(target="historico_exercicios", dry_run=False),
        )
        after_first_counts = _tracking_counts()
        second_result = import_uploaded_spreadsheet(
            SimpleUploadedFile(
                "repetidos-anonimo.xlsx",
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ImportOptions(target="historico_exercicios", dry_run=False),
        )

        self.assertTrue(first_result.saved)
        self.assertTrue(second_result.saved)
        self.assertEqual(first_result.created_count, 2)
        self.assertEqual(second_result.updated_count, 2)
        self.assertEqual(first_result.category_count, 2)
        self.assertEqual(first_result.exercise_count, 2)
        self.assertEqual(first_result.mark_count, 1)
        self.assertEqual(after_first_counts["procedure_exercises"], 2)
        self.assertEqual(after_first_counts["exercises"], 2)
        self.assertEqual(after_first_counts["session_exercises"], 1)
        self.assertEqual(_tracking_counts(), after_first_counts)

        exercises = list(ExercicioCatalogo.objects.filter(nome="Ponte").select_related("categoria").order_by("categoria__nome"))
        self.assertEqual([exercise.categoria.nome for exercise in exercises], ["Cadeira", "Reformer"])
        self.assertEqual({_normalize_test_key(exercise.nome) for exercise in exercises}, {"ponte"})
        paciente = Paciente.objects.get(nome="Paciente Repeticao")
        procedimento = Procedimento.objects.get(paciente=paciente, tipo_procedimento__nome="Pilates")
        linked_categories = set(
            ProcedimentoExercicio.objects.filter(procedimento=procedimento).values_list(
                "exercicio__categoria__nome",
                flat=True,
            )
        )
        self.assertEqual(linked_categories, {"Cadeira", "Reformer"})

    def test_reference_fixture_parser_ignores_horizontal_equipment_headers(self):
        performed_date = date(2026, 7, 6)
        upload = SimpleUploadedFile(
            "referencia-anonima.xlsx",
            _build_reference_tracking_xlsx(performed_date),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_exercise_tracking_spreadsheet(upload)
        marks = [
            (
                row["linha_origem"],
                row["categoria"],
                row["exercicio"],
                mark["data"],
                mark["marca"],
            )
            for row in data.rows
            for mark in row["marcacoes"]
        ]

        false_headers = {"TRAPÉZIO", "CADEIRA COMBO", "BARRIL", "COREALIGN", "OBSERVAÇÕES"}

        self.assertEqual(len(data.rows), 188)
        self.assertEqual(len(marks), 4)
        self.assertTrue(false_headers.isdisjoint({row["exercicio"] for row in data.rows}))
        self.assertEqual(len(marks), len(set(marks)))
        self.assertEqual({mark[3] for mark in marks}, {performed_date})

    def test_same_exercise_can_have_marks_on_different_dates(self):
        first_date = date(2026, 7, 6)
        second_date = date(2026, 7, 8)
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(first_date), _excel_serial(second_date)],
                        ["", "Solo", "Hundred", "X", "X/"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        data = read_exercise_tracking_spreadsheet(upload)

        self.assertEqual(len(data.rows), 1)
        self.assertEqual(
            data.rows[0]["marcacoes"],
            [
                {"data": first_date, "marca": "X"},
                {"data": second_date, "marca": "X/"},
            ],
        )

    def test_import_rolls_back_when_last_save_fails(self):
        upload = SimpleUploadedFile(
            "controle.xlsx",
            _build_xlsx_workbook(
                {
                    "JUL26": [
                        ["", "Paciente Teste"],
                        ["", "", "", _excel_serial(date(2026, 7, 6))],
                        ["", "Solo", "Hundred", ""],
                        ["", "Solo", "Roll Up", "X"],
                    ]
                }
            ),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        before_counts = _tracking_counts()

        with patch("importacao.services._get_or_create_tracking_session_exercise", side_effect=DatabaseError("falha simulada")):
            result = import_uploaded_spreadsheet(
                upload,
                ImportOptions(target="historico_exercicios", dry_run=False),
            )

        self.assertFalse(result.saved)
        self.assertTrue(result.has_errors)
        self.assertIn("Erro ao salvar no banco de dados", result.errors[0])
        self.assertEqual(_tracking_counts(), before_counts)


def _tracking_xlsx_for_patient(patient_name, performed_date, category="Solo", exercise="Ponte", mark="X"):
    return _build_xlsx_workbook(
        {
            "JUL26": [
                ["", patient_name],
                ["", "", "", _excel_serial(performed_date)],
                ["", category, exercise, mark],
            ]
        }
    )


def _write_tracking_file(directory, filename, patient_name):
    path = Path(directory) / filename
    path.write_bytes(_tracking_xlsx_for_patient(patient_name, date(2026, 7, 6)))
    return path


def _tracking_counts():
    return {
        "patients": Paciente.objects.count(),
        "categories": CategoriaExercicio.objects.count(),
        "exercises": ExercicioCatalogo.objects.count(),
        "procedure_types": TipoProcedimento.objects.count(),
        "procedures": Procedimento.objects.count(),
        "procedure_exercises": ProcedimentoExercicio.objects.count(),
        "sessions": Sessao.objects.count(),
        "session_exercises": SessaoExercicio.objects.count(),
    }


def _empty_tracking_counts():
    return {key: 0 for key in _tracking_counts()}


def _normalize_test_key(value):
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower())
    return normalized.strip("_")


def _build_xlsx(rows):
    return _build_xlsx_workbook({"Pacientes": rows})


def _build_xlsx_workbook(sheets, merges=None):
    merges = merges or {}
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
        for index, (name, rows) in enumerate(sheets.items(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows, merges.get(name, [])))
    return buffer.getvalue()


def _worksheet_xml(rows, merges=None):
    merges = merges or []
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            if value == "" or value is None:
                continue
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(_cell_xml(reference, value))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    merge_xml = ""
    if merges:
        merge_xml = (
            f'<mergeCells count="{len(merges)}">'
            + "".join(f'<mergeCell ref="{escape(ref)}"/>' for ref in merges)
            + "</mergeCells>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(row_xml)}
  </sheetData>
  {merge_xml}
</worksheet>"""


def _cell_xml(reference, value):
    if isinstance(value, (int, float)):
        return f'<c r="{reference}"><v>{value}</v></c>'
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _excel_serial(value):
    return (datetime.combine(value, time.min) - datetime(1899, 12, 30)).days


def _build_reference_tracking_xlsx(performed_date):
    sections = [
        ("Estabilizadores", 8, None),
        ("Exercicios de Solo", 28, None),
        ("Reformer", 28, None),
        ("Trapezio", 26, "TRAPÉZIO"),
        ("Cadeira", 15, "CADEIRA COMBO"),
        ("Barril", 11, "BARRIL"),
        ("Corealign", 72, "COREALIGN"),
    ]
    rows = [
        ["", "Paciente Referencia"],
        ["", "", "", _excel_serial(performed_date)],
    ]
    merges = ["B1:Z1", "B2:C2"]
    mark_positions = {1: "X/", 9: "X", 11: "X", 89: "X/"}
    exercise_index = 1
    row_number = 3

    for category, count, header in sections:
        if header:
            rows.append(_tracking_fixture_row(category, header))
            merges.append(f"B{row_number}:B{row_number + count}")
            merges.append(f"C{row_number}:Z{row_number}")
            row_number += 1
        else:
            merges.append(f"B{row_number}:B{row_number + count - 1}")

        for index in range(count):
            mark = mark_positions.get(exercise_index, "")
            rows.append(
                _tracking_fixture_row(
                    category if not header and index == 0 else "",
                    f"{category} Exercicio {index + 1:03d}",
                    mark,
                )
            )
            row_number += 1
            exercise_index += 1

    rows.append(["", "OBSERVAÇÕES", "", "Anotacao anonima"])
    merges.append(f"B{row_number}:Z{row_number}")
    return _build_xlsx_workbook({"JUL26": rows}, merges={"JUL26": merges})


def _tracking_fixture_row(category, exercise, mark=""):
    row = [""] * 26
    row[1] = category
    row[2] = exercise
    row[3] = mark
    return row


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
