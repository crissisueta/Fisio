import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from importacao.services import ImportOptions, TARGET_EXERCISE_TRACKING, import_uploaded_spreadsheet


SUPPORTED_SUFFIXES = {".xlsx", ".csv"}
REPORT_FIELDS = [
    "arquivo",
    "aba",
    "status",
    "tipo_erro",
    "duracao",
    "categorias",
    "exercicios",
    "marcacoes",
    "criados",
    "atualizados",
    "ignorados",
    "mensagem_erro",
]


@dataclass
class FileReport:
    arquivo: str
    aba: str = ""
    status: str = "erro"
    tipo_erro: str = ""
    duracao: float = 0.0
    categorias: int = 0
    exercicios: int = 0
    marcacoes: int = 0
    criados: int = 0
    atualizados: int = 0
    ignorados: int = 0
    mensagem_erro: str = ""

    def as_dict(self) -> dict[str, str | int | float]:
        return {
            "arquivo": self.arquivo,
            "aba": self.aba,
            "status": self.status,
            "tipo_erro": self.tipo_erro,
            "duracao": round(self.duracao, 3),
            "categorias": self.categorias,
            "exercicios": self.exercicios,
            "marcacoes": self.marcacoes,
            "criados": self.criados,
            "atualizados": self.atualizados,
            "ignorados": self.ignorados,
            "mensagem_erro": self.mensagem_erro,
        }


class Command(BaseCommand):
    help = "Importa historicos de exercicios a partir de um arquivo ou diretorio."

    def add_arguments(self, parser):
        parser.add_argument("caminho", help="Arquivo .xlsx/.csv ou diretorio com planilhas.")
        parser.add_argument("--dry-run", action="store_true", help="Simula a importacao sem alterar tabelas.")
        parser.add_argument("--sheet", default="", help="Nome da aba a importar. Por padrao, todas as abas do historico XLSX.")
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continua processando os proximos arquivos quando um arquivo falha.",
        )
        parser.add_argument("--report", default="", help="Caminho para relatorio .json ou .csv.")

    def handle(self, *args, **options):
        started_at = monotonic()
        source = Path(options["caminho"])
        files = _discover_files(source)
        import_options = ImportOptions(
            target=TARGET_EXERCISE_TRACKING,
            dry_run=options["dry_run"],
            update_existing=True,
            create_related=True,
        )
        reports: list[FileReport] = []
        failures = 0

        try:
            for index, file_path in enumerate(files, start=1):
                self.stdout.write(f"[{index}/{len(files)}] {file_path.name}")
                report = _process_file(file_path, import_options, options["sheet"])
                reports.append(report)
                _write_file_progress(self, report)

                if report.status == "erro":
                    failures += 1
                    if not options["continue_on_error"]:
                        break
                    if index < len(files):
                        self.stdout.write("Continuando para o proximo arquivo...")
        except KeyboardInterrupt as exc:
            if options["report"]:
                _write_report(Path(options["report"]), reports)
            raise CommandError("Importacao interrompida pelo usuario. O arquivo em andamento foi revertido.") from exc

        total_duration = monotonic() - started_at
        completed = len([report for report in reports if report.status != "erro"])
        self.stdout.write("")
        self.stdout.write(f"Processados: {len(reports)}")
        self.stdout.write(f"Concluidos: {completed}")
        self.stdout.write(f"Falharam: {failures}")
        self.stdout.write(f"Duracao total: {total_duration:.1f}s")

        if options["report"]:
            _write_report(Path(options["report"]), reports)
            self.stdout.write(f"Relatorio: {options['report']}")

        if failures:
            raise CommandError(f"Importacao concluida com {failures} falha(s).")


def _discover_files(source: Path) -> list[Path]:
    if not source.exists():
        raise CommandError(f"Caminho nao encontrado: {source}")
    if source.is_file():
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise CommandError("Informe um arquivo .xlsx ou .csv.")
        return [source]
    if not source.is_dir():
        raise CommandError(f"Caminho invalido: {source}")

    files = sorted(
        path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise CommandError("Nenhuma planilha .xlsx ou .csv encontrada.")
    return files


def _process_file(file_path: Path, options: ImportOptions, sheet_name: str) -> FileReport:
    started_at = monotonic()
    report = FileReport(arquivo=file_path.name)
    try:
        with file_path.open("rb") as handle:
            result = import_uploaded_spreadsheet(File(handle, name=file_path.name), options, sheet_name=sheet_name)
    except DatabaseError as exc:
        report.tipo_erro = "banco"
        report.mensagem_erro = _sanitize_error(str(exc))
    except OSError as exc:
        report.tipo_erro = "arquivo_invalido"
        report.mensagem_erro = _sanitize_error(str(exc))
    except Exception as exc:
        report.tipo_erro = "erro_inesperado"
        report.mensagem_erro = _sanitize_error(str(exc))
    else:
        report.aba = result.sheet_name
        report.categorias = result.category_count
        report.exercicios = result.exercise_count
        report.marcacoes = result.mark_count
        report.criados = result.created_count
        report.atualizados = result.updated_count
        report.ignorados = result.skipped_count
        if result.has_errors:
            report.tipo_erro = _classify_result_error(result)
            report.mensagem_erro = _result_error_message(result)
        else:
            report.status = "simulado" if options.dry_run else "concluido"
    report.duracao = monotonic() - started_at
    return report


def _classify_result_error(result) -> str:
    messages = " ".join(result.errors)
    if "Erro ao salvar no banco de dados" in messages:
        return "banco"
    parse_markers = ["XLSX", "Formato", "Arquivo", "Aba", "Nenhum exercicio", "planilha"]
    if result.errors and any(marker in messages for marker in parse_markers):
        return "parsing"
    return "validacao"


def _result_error_message(result) -> str:
    messages = list(result.errors)
    for row in result.rows:
        if row.errors:
            messages.append(f"linha {row.row_number}: {row.errors[0]}")
            break
    if not messages:
        return "Erro desconhecido."
    return _sanitize_error(messages[0])


def _sanitize_error(message: str) -> str:
    sanitized = re.sub(r"[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", message)
    sanitized = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[cpf]", sanitized)
    sanitized = re.sub(r"\b\d{9,}\b", "[numero]", sanitized)
    sanitized = re.sub(r"(paciente(?: nao encontrado)?(?: para CPF)?)(?: [^.;]+)?", r"\1 [redigido]", sanitized, flags=re.I)
    sanitized = re.sub(r"(exercicio)(?: [^.;]+)", r"\1 [redigido]", sanitized, flags=re.I)
    return sanitized[:300]


def _write_file_progress(command: Command, report: FileReport) -> None:
    if report.status != "erro":
        command.stdout.write(f"  categorias: {report.categorias}")
        command.stdout.write(f"  exercicios: {report.exercicios}")
        command.stdout.write(f"  marcacoes: {report.marcacoes}")
        command.stdout.write(f"  duracao: {report.duracao:.1f}s")
        command.stdout.write(f"  resultado: {report.status}")
        return

    command.stdout.write("  resultado: erro")
    command.stdout.write(f"  tipo: {report.tipo_erro}")
    command.stdout.write(f"  motivo: {report.mensagem_erro}")


def _write_report(path: Path, reports: list[FileReport]) -> None:
    rows = [report.as_dict() for report in reports]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
