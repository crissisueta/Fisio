import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Callable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from avaliacoes.models import Avaliacao, TipoAvaliacao
from exercicios.models import CategoriaExercicio, ExercicioCatalogo
from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao, TipoProcedimento

from .spreadsheets import SpreadsheetReadError, read_spreadsheet


TARGET_PATIENTS = "pacientes"
TARGET_PROCEDURE_TYPES = "tipos_procedimento"
TARGET_EVALUATION_TYPES = "tipos_avaliacao"
TARGET_EXERCISE_CATEGORIES = "categorias_exercicio"
TARGET_EXERCISES = "exercicios"
TARGET_PROCEDURES = "procedimentos"
TARGET_EVALUATIONS = "avaliacoes"
TARGET_SESSIONS = "sessoes"

TARGET_CHOICES = [
    (TARGET_PATIENTS, "Pacientes"),
    (TARGET_PROCEDURE_TYPES, "Tipos de Procedimento"),
    (TARGET_EVALUATION_TYPES, "Tipos de Avaliacao"),
    (TARGET_EXERCISE_CATEGORIES, "Categorias de Exercicio"),
    (TARGET_EXERCISES, "Exercicios"),
    (TARGET_PROCEDURES, "Procedimentos"),
    (TARGET_EVALUATIONS, "Avaliacoes"),
    (TARGET_SESSIONS, "Sessoes"),
]

ACTION_CREATE = "criar"
ACTION_UPDATE = "atualizar"
ACTION_SKIP = "pular"


@dataclass
class ImportOptions:
    target: str
    update_existing: bool = True
    create_related: bool = True
    dry_run: bool = True


@dataclass
class ImportRowResult:
    row_number: int
    action: str
    values: dict[str, str]
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "erro"
        return self.action


@dataclass
class ImportResult:
    target: str
    sheet_name: str = ""
    dry_run: bool = True
    saved: bool = False
    rows: list[ImportRowResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors or any(row.errors for row in self.rows))

    @property
    def created_count(self) -> int:
        return sum(1 for row in self.rows if not row.errors and row.action == ACTION_CREATE)

    @property
    def updated_count(self) -> int:
        return sum(1 for row in self.rows if not row.errors and row.action == ACTION_UPDATE)

    @property
    def skipped_count(self) -> int:
        return sum(1 for row in self.rows if not row.errors and row.action == ACTION_SKIP)


@dataclass
class PreparedOperation:
    preview: ImportRowResult
    save: Callable[[], None] | None = None


@dataclass(frozen=True)
class PendingRelated:
    model: type
    name: str
    defaults: dict[str, Any] = field(default_factory=dict)


COLUMN_ALIASES = {
    "e_mail": "email",
    "email": "email",
    "nome_completo": "nome",
    "nome_do_paciente": "paciente_nome",
    "paciente_nome": "paciente_nome",
    "nome_paciente": "paciente_nome",
    "paciente": "paciente_nome",
    "cpf_paciente": "paciente_cpf",
    "paciente_cpf": "paciente_cpf",
    "data_de_nascimento": "data_nascimento",
    "nascimento": "data_nascimento",
    "data_de_matricula": "data_matricula",
    "matricula": "data_matricula",
    "telefone_residencial": "telefone",
    "telefone_celular": "celular",
    "fone": "telefone",
    "convenio": "plano",
    "plano_de_saude": "plano",
    "observacao": "observacoes",
    "observacoes": "observacoes",
    "descricao": "descricao",
    "tipo": "tipo",
    "tipo_procedimento": "tipo_procedimento",
    "procedimento_tipo": "tipo_procedimento",
    "tipo_de_procedimento": "tipo_procedimento",
    "tipo_avaliacao": "tipo_avaliacao",
    "tipo_de_avaliacao": "tipo_avaliacao",
    "data": "data",
    "hora": "hora",
    "horario": "hora",
    "data_hora": "data_hora",
    "data_e_hora": "data_hora",
    "procedimento": "procedimento_id",
    "procedimento_id": "procedimento_id",
    "id_procedimento": "procedimento_id",
    "sessao": "sessao_id",
    "sessao_id": "sessao_id",
    "id_sessao": "sessao_id",
    "avaliacao": "avaliacao_id",
    "avaliacao_id": "avaliacao_id",
    "id_avaliacao": "avaliacao_id",
    "id": "id",
    "duracao": "duracao_minutos",
    "duracao_minutos": "duracao_minutos",
    "hora_final": "hora_final",
    "fim": "hora_final",
    "assinatura": "assinatura_confirmada",
    "assinatura_confirmada": "assinatura_confirmada",
    "categoria": "categoria",
    "categoria_exercicio": "categoria",
    "instrucoes": "instrucoes",
    "ativo": "ativo",
    "disponivel": "ativo",
    "max_sessoes_consecutivas": "max_sessoes_consecutivas",
    "sessoes_ate_cooldown": "sessoes_ate_cooldown",
}


def import_uploaded_spreadsheet(uploaded_file, options: ImportOptions, sheet_name: str = "") -> ImportResult:
    try:
        spreadsheet = read_spreadsheet(uploaded_file, sheet_name=sheet_name)
    except SpreadsheetReadError as exc:
        return ImportResult(target=options.target, dry_run=options.dry_run, errors=[str(exc)])

    result = import_rows(spreadsheet.rows, options, sheet_name=spreadsheet.sheet_name)
    return result


def import_rows(rows: list[dict[str, Any]], options: ImportOptions, sheet_name: str = "") -> ImportResult:
    result = ImportResult(target=options.target, sheet_name=sheet_name, dry_run=options.dry_run)
    importer = _importer_for_target(options.target)
    operations: list[PreparedOperation] = []
    seen: dict[str, int] = {}

    for index, raw_row in enumerate(rows, start=2):
        row = _canonicalize_row(raw_row)
        operation = importer(row, index, options, seen)
        operations.append(operation)
        result.rows.append(operation.preview)

    if result.has_errors or options.dry_run:
        return result

    try:
        with transaction.atomic():
            for operation in operations:
                if operation.save and operation.preview.action != ACTION_SKIP:
                    operation.save()
    except ValidationError as exc:
        result.errors.append(_validation_message(exc))
        return result

    result.saved = True
    return result


def _importer_for_target(target: str):
    importers = {
        TARGET_PATIENTS: _prepare_patient,
        TARGET_PROCEDURE_TYPES: _prepare_procedure_type,
        TARGET_EVALUATION_TYPES: _prepare_evaluation_type,
        TARGET_EXERCISE_CATEGORIES: _prepare_exercise_category,
        TARGET_EXERCISES: _prepare_exercise,
        TARGET_PROCEDURES: _prepare_procedure,
        TARGET_EVALUATIONS: _prepare_evaluation,
        TARGET_SESSIONS: _prepare_session,
    }
    try:
        return importers[target]
    except KeyError as exc:
        raise ValueError(f"Destino de importacao invalido: {target}") from exc


def _prepare_patient(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    cpf = _text(row.get("cpf"))
    _track_unique("paciente", cpf, row_number, seen, errors)

    values = {
        "nome": _required_text(row, "nome", errors),
        "cpf": _required_text(row, "cpf", errors),
        "email": _required_text(row, "email", errors),
        "profissao": _text(row.get("profissao")),
        "endereco": _required_text(row, "endereco", errors),
        "bairro": _required_text(row, "bairro", errors),
        "cep": _required_text(row, "cep", errors),
        "telefone": _text(row.get("telefone")),
        "celular": _required_text(row, "celular", errors),
        "telefone_comercial": _text(row.get("telefone_comercial")),
        "data_nascimento": _parse_date(row.get("data_nascimento"), "data_nascimento", errors),
        "data_matricula": _parse_date(row.get("data_matricula"), "data_matricula", errors),
        "plano": _required_text(row, "plano", errors),
        "observacoes": _text(row.get("observacoes")),
    }

    existing = Paciente.all_objects.filter(cpf=cpf).first() if cpf else None
    action = _existing_action(existing, options)
    display = _display_values(values, ["nome", "cpf", "email", "celular", "plano"])
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    obj = existing or Paciente()
    _assign(obj, values)
    _restore_if_needed(obj)
    _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else obj.save)


def _prepare_procedure_type(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    nome = _required_any_text(row, ["nome", "tipo"], "nome", errors)
    _track_unique("tipo_procedimento", _key(nome), row_number, seen, errors)

    existing = _find_by_name(TipoProcedimento, nome) if nome else None
    action = _existing_action(existing, options)
    values = {
        "nome": nome,
        "habilita_exercicios": _parse_bool(
            row.get("habilita_exercicios"),
            default=existing.habilita_exercicios if existing else False,
        ),
    }
    display = _display_values(values, ["nome", "habilita_exercicios"])
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    obj = existing or TipoProcedimento()
    _assign(obj, values)
    _restore_if_needed(obj)
    _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else obj.save)


def _prepare_evaluation_type(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    nome = _required_any_text(row, ["nome", "tipo"], "nome", errors)
    _track_unique("tipo_avaliacao", _key(nome), row_number, seen, errors)

    existing = _find_by_name(TipoAvaliacao, nome) if nome else None
    action = _existing_action(existing, options)
    values = {"nome": nome}
    display = _display_values(values, ["nome"])
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    obj = existing or TipoAvaliacao()
    _assign(obj, values)
    _restore_if_needed(obj)
    _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else obj.save)


def _prepare_exercise_category(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    nome = _required_any_text(row, ["nome", "categoria"], "nome", errors)
    _track_unique("categoria", _key(nome), row_number, seen, errors)

    existing = _find_by_name(CategoriaExercicio, nome) if nome else None
    action = _existing_action(existing, options)
    values = {
        "nome": nome,
        "descricao": _text(row.get("descricao")),
    }
    display = _display_values(values, ["nome", "descricao"])
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    obj = existing or CategoriaExercicio()
    _assign(obj, values)
    _restore_if_needed(obj)
    _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else obj.save)


def _prepare_exercise(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    nome = _required_text(row, "nome", errors)
    categoria_nome = _required_text(row, "categoria", errors)
    _track_unique("exercicio", _key(nome), row_number, seen, errors)

    categoria = _resolve_category(categoria_nome, options, errors) if categoria_nome else None
    existing = _find_by_name(ExercicioCatalogo, nome) if nome else None
    action = _existing_action(existing, options)
    values = {
        "nome": nome,
        "categoria": categoria,
        "descricao": _text(row.get("descricao")),
        "instrucoes": _text(row.get("instrucoes")),
        "observacoes": _text(row.get("observacoes")),
        "ativo": _parse_bool(row.get("ativo"), default=existing.ativo if existing else True),
        "max_sessoes_consecutivas": _parse_positive_int(
            row.get("max_sessoes_consecutivas"),
            "max_sessoes_consecutivas",
            errors,
            default=existing.max_sessoes_consecutivas if existing else 2,
        ),
        "sessoes_ate_cooldown": _parse_positive_int(
            row.get("sessoes_ate_cooldown"),
            "sessoes_ate_cooldown",
            errors,
            default=existing.sessoes_ate_cooldown if existing else 2,
        ),
    }
    display = {
        "nome": _text(nome),
        "categoria": _text(categoria_nome),
        "ativo": _format_value(values["ativo"]),
    }
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    def save():
        resolved_categoria = _materialize_related(categoria)
        obj = existing or ExercicioCatalogo()
        _assign(obj, {**values, "categoria": resolved_categoria})
        _restore_if_needed(obj)
        obj.full_clean()
        obj.save()

    if not isinstance(categoria, PendingRelated):
        obj = existing or ExercicioCatalogo()
        _assign(obj, values)
        _restore_if_needed(obj)
        _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else save)


def _prepare_procedure(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    existing = _object_by_id(Procedimento, _first(row, "procedimento_id", "id"), "procedimento_id", errors)
    paciente = _resolve_patient(row, errors, required=existing is None)
    tipo_nome = _text(_first(row, "tipo_procedimento", "tipo"))
    tipo = _resolve_procedure_type(tipo_nome, options, errors) if tipo_nome else None
    if not existing and not tipo_nome:
        errors.append("Informe tipo_procedimento.")

    action = ACTION_UPDATE if existing and options.update_existing else ACTION_SKIP if existing else ACTION_CREATE
    values = {
        "paciente": paciente or (existing.paciente if existing else None),
        "tipo_procedimento": tipo or (existing.tipo_procedimento if existing else None),
        "observacoes": _text(row.get("observacoes")),
        "concluido": _parse_bool(row.get("concluido"), default=existing.concluido if existing else False),
    }
    display = {
        "paciente": _patient_display(values["paciente"], row),
        "tipo_procedimento": tipo_nome or _related_name(values["tipo_procedimento"]),
        "concluido": _format_value(values["concluido"]),
    }
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    def save():
        resolved_tipo = _materialize_related(values["tipo_procedimento"])
        obj = existing or Procedimento()
        _assign(obj, {**values, "tipo_procedimento": resolved_tipo})
        _restore_if_needed(obj)
        obj.full_clean()
        obj.save()

    if not isinstance(values["tipo_procedimento"], PendingRelated):
        obj = existing or Procedimento()
        _assign(obj, values)
        _restore_if_needed(obj)
        _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else save)


def _prepare_evaluation(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    existing = _object_by_id(Avaliacao, _first(row, "avaliacao_id", "id"), "avaliacao_id", errors)
    paciente = _resolve_patient(row, errors, required=existing is None)
    tipo_nome = _text(_first(row, "tipo_avaliacao", "tipo"))
    tipo = _resolve_evaluation_type(tipo_nome, options, errors) if tipo_nome else None
    if not existing and not tipo_nome:
        errors.append("Informe tipo_avaliacao.")

    data_hora = _parse_datetime_from_row(row, "data_hora", errors)
    action = ACTION_UPDATE if existing and options.update_existing else ACTION_SKIP if existing else ACTION_CREATE
    values = {
        "paciente": paciente or (existing.paciente if existing else None),
        "tipo_avaliacao": tipo or (existing.tipo_avaliacao if existing else None),
        "data_hora": data_hora or (existing.data_hora if existing else None),
        "concluida": _parse_bool(row.get("concluida"), default=existing.concluida if existing else False),
        "observacoes": _text(row.get("observacoes")),
    }
    display = {
        "paciente": _patient_display(values["paciente"], row),
        "tipo_avaliacao": tipo_nome or _related_name(values["tipo_avaliacao"]),
        "data_hora": _format_value(values["data_hora"]),
    }
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    def save():
        resolved_tipo = _materialize_related(values["tipo_avaliacao"])
        obj = existing or Avaliacao()
        _assign(obj, {**values, "tipo_avaliacao": resolved_tipo})
        _restore_if_needed(obj)
        obj.full_clean()
        obj.save()

    if not isinstance(values["tipo_avaliacao"], PendingRelated):
        obj = existing or Avaliacao()
        _assign(obj, values)
        _restore_if_needed(obj)
        _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else save)


def _prepare_session(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    existing = _object_by_id(Sessao, _first(row, "sessao_id", "id"), "sessao_id", errors)
    procedimento = _resolve_procedure(row, options, errors, required=existing is None)
    data_hora = _parse_datetime_from_row(row, "data_hora", errors)

    action = ACTION_UPDATE if existing and options.update_existing else ACTION_SKIP if existing else ACTION_CREATE
    values = {
        "procedimento": procedimento or (existing.procedimento if existing else None),
        "data_hora": data_hora or (existing.data_hora if existing else None),
        "duracao_minutos": _session_duration(row, data_hora or (existing.data_hora if existing else None), existing, errors),
        "numero": _parse_optional_positive_int(row.get("numero"), "numero", errors),
        "status": _parse_status(row.get("status"), default=existing.status if existing else Sessao.STATUS_AGENDADA, errors=errors),
        "assinatura_confirmada": _parse_bool(
            row.get("assinatura_confirmada"),
            default=existing.assinatura_confirmada if existing else False,
        ),
        "observacoes": _text(row.get("observacoes")),
    }
    if existing and values["numero"] is None:
        values["numero"] = existing.numero

    display = {
        "procedimento": _procedure_display(values["procedimento"], row),
        "data_hora": _format_value(values["data_hora"]),
        "status": values["status"],
    }
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    def save():
        resolved_procedimento = _materialize_procedure(values["procedimento"])
        obj = existing or Sessao()
        _assign(obj, {**values, "procedimento": resolved_procedimento})
        _restore_if_needed(obj)
        obj.full_clean()
        obj.save()

    if not isinstance(values["procedimento"], PendingRelated):
        obj = existing or Sessao()
        _assign(obj, values)
        _restore_if_needed(obj)
        _collect_model_errors(obj, errors)
    return PreparedOperation(ImportRowResult(row_number, action, display, errors), save=None if errors else save)


def _canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for header, value in row.items():
        key = COLUMN_ALIASES.get(_normalize_header(header), _normalize_header(header))
        if key not in canonical or _is_blank(canonical[key]):
            canonical[key] = value
    return canonical


def _normalize_header(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return text.strip("_")


def _track_unique(prefix: str, value: str, row_number: int, seen: dict[str, int], errors: list[str]) -> None:
    if not value:
        return
    key = f"{prefix}:{value}"
    if key in seen:
        errors.append(f"Duplicado na planilha: linha {seen[key]}.")
    else:
        seen[key] = row_number


def _existing_action(existing, options: ImportOptions) -> str:
    if existing is None:
        return ACTION_CREATE
    return ACTION_UPDATE if options.update_existing else ACTION_SKIP


def _assign(obj, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(obj, key, value)


def _restore_if_needed(obj) -> None:
    if hasattr(obj, "is_active"):
        obj.is_active = True
        obj.deleted_at = None


def _collect_model_errors(obj, errors: list[str]) -> None:
    if errors:
        return
    try:
        obj.full_clean()
    except ValidationError as exc:
        errors.append(_validation_message(exc))


def _validation_message(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        parts = []
        for field, messages in exc.message_dict.items():
            label = field if field != "__all__" else "registro"
            parts.append(f"{label}: {' '.join(messages)}")
        return "; ".join(parts)
    return " ".join(exc.messages)


def _required_text(row: dict[str, Any], key: str, errors: list[str]) -> str:
    value = _text(row.get(key))
    if not value:
        errors.append(f"Informe {key}.")
    return value


def _required_any_text(row: dict[str, Any], keys: list[str], label: str, errors: list[str]) -> str:
    for key in keys:
        value = _text(row.get(key))
        if value:
            return value
    errors.append(f"Informe {label}.")
    return ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sim" if value else "nao"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _key(value: Any) -> str:
    return _normalize_header(_text(value))


def _is_blank(value: Any) -> bool:
    return _text(value) == ""


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if not _is_blank(value):
            return value
    return ""


def _display_values(values: dict[str, Any], keys: list[str]) -> dict[str, str]:
    return {key: _format_value(values.get(key)) for key in keys if key in values}


def _format_value(value: Any) -> str:
    if isinstance(value, PendingRelated):
        return value.name
    if hasattr(value, "nome"):
        return value.nome
    if isinstance(value, Paciente):
        return f"{value.nome} ({value.cpf})"
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, bool):
        return "sim" if value else "nao"
    return _text(value)


def _parse_bool(value: Any, default: bool = False) -> bool:
    if _is_blank(value):
        return default
    if isinstance(value, bool):
        return value
    normalized = _key(value)
    return normalized in {"1", "sim", "s", "yes", "y", "true", "verdadeiro", "x", "ativo", "concluido"}


def _parse_positive_int(value: Any, field_name: str, errors: list[str], default: int) -> int:
    if _is_blank(value):
        return default
    parsed = _parse_optional_positive_int(value, field_name, errors)
    return default if parsed is None else parsed


def _parse_optional_positive_int(value: Any, field_name: str, errors: list[str]) -> int | None:
    if _is_blank(value):
        return None
    try:
        parsed = int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        errors.append(f"{field_name} deve ser um numero inteiro.")
        return None
    if parsed < 0:
        errors.append(f"{field_name} deve ser positivo.")
        return None
    return parsed


def _parse_date(value: Any, field_name: str, errors: list[str]) -> date | None:
    if _is_blank(value):
        errors.append(f"Informe {field_name}.")
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return _excel_datetime(value).date()

    text = _text(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        errors.append(f"{field_name} deve ser uma data valida.")
        return None


def _parse_datetime_from_row(row: dict[str, Any], field_name: str, errors: list[str]) -> datetime | None:
    value = row.get(field_name)
    if not _is_blank(value):
        return _parse_datetime(value, field_name, errors)

    date_value = row.get("data")
    time_value = _first(row, "hora", "horario")
    if _is_blank(date_value):
        errors.append(f"Informe {field_name}.")
        return None
    parsed_date = _parse_date(date_value, "data", errors)
    parsed_time = _parse_time(time_value, "hora", errors) if not _is_blank(time_value) else time(0, 0)
    if parsed_date is None or parsed_time is None:
        return None
    return _ensure_aware(datetime.combine(parsed_date, parsed_time))


def _parse_datetime(value: Any, field_name: str, errors: list[str]) -> datetime | None:
    if isinstance(value, datetime):
        return _ensure_aware(value)
    if isinstance(value, date):
        return _ensure_aware(datetime.combine(value, time(0, 0)))
    if isinstance(value, (int, float)):
        return _ensure_aware(_excel_datetime(value))

    text = _text(value)
    for fmt in (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%y %H:%M",
    ):
        try:
            return _ensure_aware(datetime.strptime(text, fmt))
        except ValueError:
            continue
    try:
        return _ensure_aware(datetime.fromisoformat(text))
    except ValueError:
        errors.append(f"{field_name} deve ser data e hora validas.")
        return None


def _parse_time(value: Any, field_name: str, errors: list[str]) -> time | None:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, (int, float)):
        _, seconds = divmod(float(value) * 24 * 60 * 60, 24 * 60 * 60)
        hours, seconds = divmod(int(seconds), 3600)
        minutes, seconds = divmod(seconds, 60)
        return time(hours, minutes, seconds)
    text = _text(value)
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    errors.append(f"{field_name} deve ser um horario valido.")
    return None


def _excel_datetime(value: int | float) -> datetime:
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def _ensure_aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _find_by_name(model, name: str):
    if not name:
        return None
    return model.all_objects.filter(nome__iexact=name).first()


def _resolve_category(name: str, options: ImportOptions, errors: list[str]):
    category = _find_by_name(CategoriaExercicio, name)
    if category:
        return category
    if options.create_related:
        return PendingRelated(CategoriaExercicio, name)
    errors.append(f"Categoria nao encontrada: {name}.")
    return None


def _resolve_procedure_type(name: str, options: ImportOptions, errors: list[str]):
    procedure_type = _find_by_name(TipoProcedimento, name)
    if procedure_type:
        return procedure_type
    if options.create_related:
        return PendingRelated(TipoProcedimento, name)
    errors.append(f"Tipo de procedimento nao encontrado: {name}.")
    return None


def _resolve_evaluation_type(name: str, options: ImportOptions, errors: list[str]):
    evaluation_type = _find_by_name(TipoAvaliacao, name)
    if evaluation_type:
        return evaluation_type
    if options.create_related:
        return PendingRelated(TipoAvaliacao, name)
    errors.append(f"Tipo de avaliacao nao encontrado: {name}.")
    return None


def _materialize_related(value):
    if not isinstance(value, PendingRelated):
        return value
    obj = _find_by_name(value.model, value.name)
    if obj is None:
        obj = value.model(nome=value.name, **value.defaults)
    _restore_if_needed(obj)
    obj.full_clean()
    obj.save()
    return obj


def _resolve_patient(row: dict[str, Any], errors: list[str], required: bool = True):
    cpf = _text(_first(row, "paciente_cpf", "cpf"))
    if cpf:
        paciente = Paciente.objects.filter(cpf=cpf).first()
        if paciente is None:
            errors.append(f"Paciente nao encontrado para CPF {cpf}.")
        return paciente

    name = _text(_first(row, "paciente_nome"))
    if name:
        matches = list(Paciente.objects.filter(nome__iexact=name)[:2])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            errors.append(f"Mais de um paciente encontrado com nome {name}. Informe o CPF.")
            return None
        errors.append(f"Paciente nao encontrado: {name}.")
        return None

    if required:
        errors.append("Informe paciente_cpf ou paciente_nome.")
    return None


def _object_by_id(model, value: Any, field_name: str, errors: list[str]):
    if _is_blank(value):
        return None
    try:
        object_id = int(float(str(value)))
    except ValueError:
        errors.append(f"{field_name} deve ser um ID valido.")
        return None
    obj = model.all_objects.filter(pk=object_id).first()
    if obj is None:
        errors.append(f"{model._meta.verbose_name} nao encontrado para ID {object_id}.")
    return obj


def _resolve_procedure(row: dict[str, Any], options: ImportOptions, errors: list[str], required: bool = True):
    existing = _object_by_id(Procedimento, row.get("procedimento_id"), "procedimento_id", errors)
    if existing:
        return existing

    paciente = _resolve_patient(row, errors, required=required)
    tipo_nome = _text(_first(row, "tipo_procedimento", "tipo"))
    if not tipo_nome:
        if required:
            errors.append("Informe tipo_procedimento.")
        return None

    tipo = _resolve_procedure_type(tipo_nome, options, errors)
    if paciente is None or tipo is None:
        return None

    if isinstance(tipo, PendingRelated):
        if options.create_related:
            return PendingRelated(Procedimento, "", {"paciente": paciente, "tipo_procedimento": tipo})
        return None

    matches = list(Procedimento.objects.filter(paciente=paciente, tipo_procedimento=tipo)[:2])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        errors.append("Mais de um procedimento ativo encontrado. Informe procedimento_id.")
        return None
    if not options.create_related:
        errors.append("Procedimento nao encontrado.")
        return None
    return PendingRelated(Procedimento, "", {"paciente": paciente, "tipo_procedimento": tipo})


def _materialize_procedure(value):
    if not isinstance(value, PendingRelated) or value.model is not Procedimento:
        return _materialize_related(value)

    paciente = value.defaults["paciente"]
    tipo = _materialize_related(value.defaults["tipo_procedimento"])
    obj = Procedimento.objects.filter(paciente=paciente, tipo_procedimento=tipo).first()
    if obj is None:
        obj = Procedimento(paciente=paciente, tipo_procedimento=tipo)
        obj.full_clean()
        obj.save()
    return obj


def _session_duration(row: dict[str, Any], data_hora: datetime | None, existing: Sessao | None, errors: list[str]) -> int:
    duration = _parse_positive_int(
        row.get("duracao_minutos"),
        "duracao_minutos",
        errors,
        default=existing.duracao_minutos if existing else 60,
    )
    hora_final = row.get("hora_final")
    if _is_blank(hora_final) or data_hora is None:
        return duration

    parsed_end = _parse_time(hora_final, "hora_final", errors)
    if parsed_end is None:
        return duration
    local_start = timezone.localtime(data_hora)
    minutes = int(
        (
            datetime.combine(local_start.date(), parsed_end)
            - datetime.combine(local_start.date(), local_start.time().replace(tzinfo=None))
        ).total_seconds()
        // 60
    )
    if minutes <= 0:
        errors.append("hora_final deve ser maior que o horario inicial.")
        return duration
    return minutes


def _parse_status(value: Any, default: str, errors: list[str]) -> str:
    if _is_blank(value):
        return default
    normalized = _key(value)
    choices = {
        _key(choice_value): choice_value
        for choice_value, _label in Sessao.STATUS_CHOICES
    }
    choices.update({_key(label): choice_value for choice_value, label in Sessao.STATUS_CHOICES})
    if normalized in choices:
        return choices[normalized]
    errors.append("Status invalido.")
    return default


def _patient_display(paciente, row: dict[str, Any]) -> str:
    if paciente is not None:
        return _format_value(paciente)
    return _text(_first(row, "paciente_cpf", "cpf", "paciente_nome"))


def _procedure_display(procedimento, row: dict[str, Any]) -> str:
    if isinstance(procedimento, PendingRelated):
        paciente = procedimento.defaults.get("paciente")
        tipo = procedimento.defaults.get("tipo_procedimento")
        return f"{_format_value(paciente)} - {_format_value(tipo)}"
    if procedimento is not None:
        return str(procedimento)
    return _text(_first(row, "procedimento_id", "paciente_cpf", "cpf", "paciente_nome"))


def _related_name(value) -> str:
    return _format_value(value)
