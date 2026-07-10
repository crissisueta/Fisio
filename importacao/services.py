import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Callable

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone

from avaliacoes.models import Avaliacao, TipoAvaliacao
from exercicios.models import CategoriaExercicio, ExercicioCatalogo, ProcedimentoExercicio, SessaoExercicio
from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao, TipoProcedimento
from procedimentos.services.scheduling import resequence_sessoes

from .spreadsheets import SpreadsheetReadError, read_exercise_tracking_spreadsheet, read_spreadsheet


TARGET_PATIENTS = "pacientes"
TARGET_PROCEDURE_TYPES = "tipos_procedimento"
TARGET_EVALUATION_TYPES = "tipos_avaliacao"
TARGET_EXERCISE_CATEGORIES = "categorias_exercicio"
TARGET_EXERCISES = "exercicios"
TARGET_PROCEDURES = "procedimentos"
TARGET_EVALUATIONS = "avaliacoes"
TARGET_SESSIONS = "sessoes"
TARGET_EXERCISE_TRACKING = "historico_exercicios"

TARGET_CHOICES = [
    (TARGET_PATIENTS, "Pacientes"),
    (TARGET_PROCEDURE_TYPES, "Tipos de Procedimento"),
    (TARGET_EVALUATION_TYPES, "Tipos de Avaliacao"),
    (TARGET_EXERCISE_CATEGORIES, "Categorias de Exercicio"),
    (TARGET_EXERCISES, "Exercicios"),
    (TARGET_PROCEDURES, "Procedimentos"),
    (TARGET_EVALUATIONS, "Avaliacoes"),
    (TARGET_SESSIONS, "Sessoes"),
    (TARGET_EXERCISE_TRACKING, "Historico de Exercicios"),
]

ACTION_CREATE = "criar"
ACTION_UPDATE = "atualizar"
ACTION_SKIP = "pular"
TRACKING_IMPORT_PROCEDURE_TYPE_NAME = "Pilates"
TRACKING_IMPORT_SESSION_OBSERVATION = "Criada pela importacao de historico de exercicios."


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
    save: Callable[..., Any] | None = None


@dataclass(frozen=True)
class PendingRelated:
    model: type
    name: str
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackingImportSaveContext:
    patients: dict[str, Paciente] = field(default_factory=dict)
    categories: dict[str, CategoriaExercicio] = field(default_factory=dict)
    exercises: dict[str, ExercicioCatalogo] = field(default_factory=dict)
    procedure_type: TipoProcedimento | None = None
    procedures: dict[tuple[int, int], Procedimento] = field(default_factory=dict)
    procedure_exercises: dict[tuple[int, int], ProcedimentoExercicio] = field(default_factory=dict)
    sessions: dict[tuple[int, date], Sessao] = field(default_factory=dict)
    session_exercises: dict[tuple[int, int], SessaoExercicio] = field(default_factory=dict)
    next_procedure_exercise_order: dict[int, int] = field(default_factory=dict)
    next_session_exercise_order: dict[int, int] = field(default_factory=dict)


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
    "exercicio": "exercicio",
    "nome_exercicio": "exercicio",
    "nome_do_exercicio": "exercicio",
    "marca": "marca",
    "marcacao": "marca",
    "aba": "sheet_name",
    "sheet": "sheet_name",
    "sheet_name": "sheet_name",
    "linha": "linha_origem",
    "linha_origem": "linha_origem",
    "instrucoes": "instrucoes",
    "ativo": "ativo",
    "disponivel": "ativo",
    "max_sessoes_consecutivas": "max_sessoes_consecutivas",
    "sessoes_ate_cooldown": "sessoes_ate_cooldown",
}


def import_uploaded_spreadsheet(uploaded_file, options: ImportOptions, sheet_name: str = "") -> ImportResult:
    try:
        if options.target == TARGET_EXERCISE_TRACKING:
            spreadsheet = read_exercise_tracking_spreadsheet(uploaded_file, sheet_name=sheet_name)
        else:
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
        save_context = _save_context_for_target(options.target)
        touched_tracking_procedure_ids: set[int] = set()
        with transaction.atomic():
            for operation in operations:
                if operation.save and operation.preview.action != ACTION_SKIP:
                    saved_value = operation.save(save_context) if save_context else operation.save()
                    if options.target == TARGET_EXERCISE_TRACKING and saved_value:
                        touched_tracking_procedure_ids.add(int(saved_value))

            for procedimento_id in sorted(touched_tracking_procedure_ids):
                resequence_sessoes(procedimento_id)
    except ValidationError as exc:
        result.errors.append(_validation_message(exc))
        return result
    except DatabaseError as exc:
        result.errors.append(f"Erro ao salvar no banco de dados: {exc}")
        return result

    result.saved = True
    return result


def _save_context_for_target(target: str) -> TrackingImportSaveContext | None:
    if target == TARGET_EXERCISE_TRACKING:
        return TrackingImportSaveContext()
    return None


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
        TARGET_EXERCISE_TRACKING: _prepare_exercise_tracking,
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


def _prepare_exercise_tracking(row: dict[str, Any], row_number: int, options: ImportOptions, seen: dict[str, int]):
    errors: list[str] = []
    paciente = _resolve_tracking_patient(row, options, errors)
    performed_date = _parse_date(row.get("data"), "data", errors)
    categoria_nome = _text(row.get("categoria")) or "Sem categoria"
    exercicio_nome = _required_text(row, "exercicio", errors)
    marca = _required_text(row, "marca", errors)
    sheet_name = _text(row.get("sheet_name"))
    source_row = _text(row.get("linha_origem"))

    _validate_max_length("categoria", categoria_nome, 100, errors)
    _validate_max_length("exercicio", exercicio_nome, 150, errors)
    _validate_tracking_related(categoria_nome, exercicio_nome, paciente, options, errors)

    duplicate_of = None
    if paciente and performed_date and exercicio_nome:
        unique_key = f"{_tracking_patient_key(paciente)}:{performed_date.isoformat()}:{_key(exercicio_nome)}"
        duplicate_of = seen.get(unique_key)
        if duplicate_of is None:
            seen[unique_key] = row_number

    existing = (
        _find_existing_tracking_mark(paciente, exercicio_nome, performed_date)
        if isinstance(paciente, Paciente) and performed_date is not None and exercicio_nome
        else None
    )
    action = ACTION_SKIP if duplicate_of is not None else _existing_action(existing, options)
    display = {
        "paciente": _format_value(paciente) if paciente else _text(_first(row, "paciente_cpf", "cpf", "paciente_nome")),
        "data": _format_value(performed_date),
        "categoria": categoria_nome,
        "exercicio": exercicio_nome,
        "marca": marca,
    }
    if sheet_name:
        display["aba"] = sheet_name
    if source_row:
        display["linha"] = source_row
    if duplicate_of is not None:
        display["duplicado_da_linha"] = str(duplicate_of)
    if action == ACTION_SKIP:
        return PreparedOperation(ImportRowResult(row_number, action, display, errors))

    def save(context: TrackingImportSaveContext):
        resolved_paciente = _materialize_tracking_patient(paciente, context)
        categoria = _get_or_create_tracking_category(categoria_nome, context)
        exercicio = _get_or_create_tracking_exercise(exercicio_nome, categoria, options, context)
        tipo_procedimento = _get_or_create_tracking_procedure_type(context)
        procedimento = _get_or_create_tracking_procedure(resolved_paciente, tipo_procedimento, context)
        procedimento_exercicio = _get_or_create_tracking_procedure_exercise(procedimento, exercicio, context)
        sessao = _get_or_create_tracking_session(procedimento, performed_date, context)
        _get_or_create_tracking_session_exercise(
            sessao,
            procedimento_exercicio,
            marca=marca,
            sheet_name=sheet_name,
            source_row=source_row,
            context=context,
        )
        return procedimento.pk

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


def _validate_max_length(field_name: str, value: str, max_length: int, errors: list[str]) -> None:
    if len(value) > max_length:
        errors.append(f"{field_name} deve ter no maximo {max_length} caracteres.")


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


def _resolve_tracking_patient(
    row: dict[str, Any],
    options: ImportOptions,
    errors: list[str],
) -> Paciente | PendingRelated | None:
    cpf = _text(_first(row, "paciente_cpf", "cpf"))
    if cpf:
        paciente = Paciente.all_objects.filter(cpf=cpf).first()
        if paciente is not None:
            return paciente
        if not options.create_related:
            errors.append(f"Paciente nao encontrado para CPF {cpf}.")
            return None

    name = _text(_first(row, "paciente_nome"))
    if not name:
        errors.append("Informe paciente_cpf ou paciente_nome.")
        return None

    matches = list(Paciente.all_objects.filter(nome__iexact=name)[:2])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        errors.append(f"Mais de um paciente encontrado com nome {name}. Informe o CPF.")
        return None

    if not options.create_related:
        errors.append(f"Paciente nao encontrado: {name}.")
        return None

    defaults = {
        "cpf": cpf or None,
        "observacoes": "Cadastro criado automaticamente pela importacao de historico de exercicios.",
    }
    return PendingRelated(Paciente, name, defaults)


def _tracking_patient_key(paciente: Paciente | PendingRelated) -> str:
    if isinstance(paciente, PendingRelated):
        return f"novo:{_key(paciente.name)}"
    return f"id:{paciente.pk}"


def _tracking_patient_cache_key(paciente: Paciente | PendingRelated) -> str:
    if isinstance(paciente, Paciente):
        if paciente.pk:
            return f"id:{paciente.pk}"
        if paciente.cpf:
            return f"cpf:{paciente.cpf}"
        return f"name:{_key(paciente.nome)}"
    cpf = _text(paciente.defaults.get("cpf"))
    if cpf:
        return f"cpf:{cpf}"
    return f"name:{_key(paciente.name)}"


def _cache_tracking_patient(
    context: TrackingImportSaveContext | None,
    paciente: Paciente,
    requested: Paciente | PendingRelated | None = None,
) -> None:
    if context is None:
        return
    if requested is not None:
        context.patients[_tracking_patient_cache_key(requested)] = paciente
    if paciente.pk:
        context.patients[f"id:{paciente.pk}"] = paciente
    if paciente.cpf:
        context.patients[f"cpf:{paciente.cpf}"] = paciente
    if paciente.nome:
        context.patients[f"name:{_key(paciente.nome)}"] = paciente


def _tracking_restore_needed(obj) -> bool:
    return hasattr(obj, "is_active") and (not obj.is_active or obj.deleted_at is not None)


def _save_tracking_object(obj, changed: bool = False) -> None:
    if obj.pk is not None and not changed and not _tracking_restore_needed(obj):
        return
    _restore_if_needed(obj)
    obj.full_clean()
    obj.save()


def _materialize_tracking_patient(
    paciente: Paciente | PendingRelated | None,
    context: TrackingImportSaveContext | None = None,
) -> Paciente:
    if isinstance(paciente, (Paciente, PendingRelated)) and context is not None:
        cached = context.patients.get(_tracking_patient_cache_key(paciente))
        if cached is not None:
            return cached

    if isinstance(paciente, Paciente):
        _save_tracking_object(paciente)
        _cache_tracking_patient(context, paciente, paciente)
        return paciente
    if not isinstance(paciente, PendingRelated) or paciente.model is not Paciente:
        raise ValidationError("Paciente nao encontrado para importar o historico de exercicios.")

    cpf = _text(paciente.defaults.get("cpf"))
    existing = Paciente.all_objects.filter(cpf=cpf).first() if cpf else None
    if existing is None:
        existing = _find_by_name(Paciente, paciente.name)
    if existing is not None:
        _save_tracking_object(existing)
        _cache_tracking_patient(context, existing, paciente)
        return existing

    obj = Paciente(nome=paciente.name, **paciente.defaults)
    _save_tracking_object(obj, changed=True)
    _cache_tracking_patient(context, obj, paciente)
    return obj


def _validate_tracking_related(
    categoria_nome: str,
    exercicio_nome: str,
    paciente: Paciente | PendingRelated | None,
    options: ImportOptions,
    errors: list[str],
) -> None:
    if options.create_related:
        return

    if categoria_nome and _find_by_name(CategoriaExercicio, categoria_nome) is None:
        errors.append(f"Categoria nao encontrada: {categoria_nome}.")
    if exercicio_nome and _find_by_name(ExercicioCatalogo, exercicio_nome) is None:
        errors.append(f"Exercicio nao encontrado: {exercicio_nome}.")

    tipo = _find_by_name(TipoProcedimento, TRACKING_IMPORT_PROCEDURE_TYPE_NAME)
    if tipo is None:
        errors.append(f"Tipo de procedimento nao encontrado: {TRACKING_IMPORT_PROCEDURE_TYPE_NAME}.")
        return
    if isinstance(paciente, Paciente) and not Procedimento.objects.filter(paciente=paciente, tipo_procedimento=tipo).exists():
        errors.append("Procedimento de historico de exercicios nao encontrado.")


def _find_existing_tracking_mark(
    paciente: Paciente,
    exercicio_nome: str,
    performed_date: date,
) -> SessaoExercicio | None:
    exercicio = _find_by_name(ExercicioCatalogo, exercicio_nome)
    if exercicio is None:
        return None

    start_datetime, end_datetime = _day_datetime_range(performed_date)
    return (
        SessaoExercicio.all_objects.filter(
            sessao__procedimento__paciente=paciente,
            sessao__data_hora__gte=start_datetime,
            sessao__data_hora__lte=end_datetime,
            exercicio=exercicio,
        )
        .order_by("-is_active", "sessao__data_hora", "pk")
        .first()
    )


def _get_or_create_tracking_category(
    nome: str,
    context: TrackingImportSaveContext | None = None,
) -> CategoriaExercicio:
    cache_key = _key(nome)
    if context is not None and cache_key in context.categories:
        return context.categories[cache_key]

    categoria = _find_by_name(CategoriaExercicio, nome)
    if categoria is None:
        categoria = CategoriaExercicio(nome=nome)
        _save_tracking_object(categoria, changed=True)
    else:
        _save_tracking_object(categoria)
    if context is not None:
        context.categories[cache_key] = categoria
    return categoria


def _get_or_create_tracking_exercise(
    nome: str,
    categoria: CategoriaExercicio,
    options: ImportOptions,
    context: TrackingImportSaveContext | None = None,
) -> ExercicioCatalogo:
    cache_key = _key(nome)
    if context is not None and cache_key in context.exercises:
        return context.exercises[cache_key]

    exercicio = _find_by_name(ExercicioCatalogo, nome)
    changed = False
    if exercicio is None:
        exercicio = ExercicioCatalogo(nome=nome, categoria=categoria)
        changed = True
    else:
        if options.update_existing and exercicio.categoria_id != categoria.pk:
            exercicio.categoria = categoria
            changed = True
    _save_tracking_object(exercicio, changed=changed)
    if context is not None:
        context.exercises[cache_key] = exercicio
    return exercicio


def _get_or_create_tracking_procedure_type(
    context: TrackingImportSaveContext | None = None,
) -> TipoProcedimento:
    if context is not None and context.procedure_type is not None:
        return context.procedure_type

    tipo = _find_by_name(TipoProcedimento, TRACKING_IMPORT_PROCEDURE_TYPE_NAME)
    changed = False
    if tipo is None:
        tipo = TipoProcedimento(nome=TRACKING_IMPORT_PROCEDURE_TYPE_NAME, habilita_exercicios=True)
        changed = True
    else:
        if not tipo.habilita_exercicios:
            tipo.habilita_exercicios = True
            changed = True
    _save_tracking_object(tipo, changed=changed)
    if context is not None:
        context.procedure_type = tipo
    return tipo


def _get_or_create_tracking_procedure(
    paciente: Paciente,
    tipo_procedimento: TipoProcedimento,
    context: TrackingImportSaveContext | None = None,
) -> Procedimento:
    cache_key = (paciente.pk, tipo_procedimento.pk)
    if context is not None and cache_key in context.procedures:
        return context.procedures[cache_key]

    procedimento = (
        Procedimento.all_objects.filter(paciente=paciente, tipo_procedimento=tipo_procedimento)
        .order_by("-is_active", "-created_at", "-pk")
        .first()
    )
    if procedimento is None:
        procedimento = Procedimento(
            paciente=paciente,
            tipo_procedimento=tipo_procedimento,
            observacoes=TRACKING_IMPORT_SESSION_OBSERVATION,
        )
        _save_tracking_object(procedimento, changed=True)
    else:
        _save_tracking_object(procedimento)
    if context is not None:
        context.procedures[cache_key] = procedimento
    return procedimento


def _get_or_create_tracking_procedure_exercise(
    procedimento: Procedimento,
    exercicio: ExercicioCatalogo,
    context: TrackingImportSaveContext | None = None,
) -> ProcedimentoExercicio:
    cache_key = (procedimento.pk, exercicio.pk)
    if context is not None and cache_key in context.procedure_exercises:
        return context.procedure_exercises[cache_key]

    procedimento_exercicio = (
        ProcedimentoExercicio.all_objects.filter(procedimento=procedimento, exercicio=exercicio)
        .order_by("-is_active", "ordem", "pk")
        .first()
    )
    if procedimento_exercicio is None:
        next_order = _next_tracking_procedure_exercise_order(procedimento, context)
        procedimento_exercicio = ProcedimentoExercicio(
            procedimento=procedimento,
            exercicio=exercicio,
            ordem=next_order,
        )
        _save_tracking_object(procedimento_exercicio, changed=True)
    else:
        _save_tracking_object(procedimento_exercicio)
    if context is not None:
        context.procedure_exercises[cache_key] = procedimento_exercicio
    return procedimento_exercicio


def _next_tracking_procedure_exercise_order(
    procedimento: Procedimento,
    context: TrackingImportSaveContext | None,
) -> int:
    if context is not None and procedimento.pk in context.next_procedure_exercise_order:
        next_order = context.next_procedure_exercise_order[procedimento.pk]
        context.next_procedure_exercise_order[procedimento.pk] = next_order + 1
        return next_order

    next_order = (
        ProcedimentoExercicio.all_objects.filter(procedimento=procedimento, is_active=True).aggregate(
            max_order=Max("ordem")
        )["max_order"]
        or 0
    ) + 1
    if context is not None:
        context.next_procedure_exercise_order[procedimento.pk] = next_order + 1
    return next_order


def _get_or_create_tracking_session(
    procedimento: Procedimento,
    performed_date: date,
    context: TrackingImportSaveContext | None = None,
) -> Sessao:
    cache_key = (procedimento.pk, performed_date)
    if context is not None and cache_key in context.sessions:
        return context.sessions[cache_key]

    start_datetime, end_datetime = _day_datetime_range(performed_date)
    status = _tracking_session_status(performed_date)
    sessao = (
        Sessao.all_objects.filter(
            procedimento=procedimento,
            data_hora__gte=start_datetime,
            data_hora__lte=end_datetime,
        )
        .order_by("-is_active", "data_hora", "pk")
        .first()
    )
    if sessao is None:
        sessao = Sessao(
            procedimento=procedimento,
            data_hora=_tracking_session_datetime(performed_date),
            duracao_minutos=60,
            status=status,
            observacoes=TRACKING_IMPORT_SESSION_OBSERVATION,
        )
        _save_tracking_object(sessao, changed=True)
    else:
        changed = False
        if status == Sessao.STATUS_REALIZADA and sessao.status != Sessao.STATUS_REALIZADA:
            sessao.status = Sessao.STATUS_REALIZADA
            changed = True
        elif sessao.status not in {Sessao.STATUS_AGENDADA, Sessao.STATUS_REALIZADA}:
            sessao.status = status
            changed = True
        _save_tracking_object(sessao, changed=changed)
    if context is not None:
        context.sessions[cache_key] = sessao
    return sessao


def _get_or_create_tracking_session_exercise(
    sessao: Sessao,
    procedimento_exercicio: ProcedimentoExercicio,
    *,
    marca: str,
    sheet_name: str,
    source_row: str,
    context: TrackingImportSaveContext | None = None,
) -> SessaoExercicio:
    cache_key = (sessao.pk, procedimento_exercicio.exercicio_id)
    if context is not None and cache_key in context.session_exercises:
        return context.session_exercises[cache_key]

    status = (
        SessaoExercicio.STATUS_CONCLUIDO
        if sessao.status == Sessao.STATUS_REALIZADA
        else SessaoExercicio.STATUS_PLANEJADO
    )
    observacoes = _tracking_mark_observation(marca, sheet_name, source_row)
    sessao_exercicio = (
        SessaoExercicio.all_objects.filter(sessao=sessao, exercicio=procedimento_exercicio.exercicio)
        .order_by("-is_active", "pk")
        .first()
    )
    if sessao_exercicio is None:
        next_order = _next_tracking_session_exercise_order(sessao, context)
        sessao_exercicio = SessaoExercicio(
            sessao=sessao,
            exercicio=procedimento_exercicio.exercicio,
            ordem=next_order,
            series=procedimento_exercicio.series,
            repeticoes=procedimento_exercicio.repeticoes,
            frequencia=procedimento_exercicio.frequencia,
            progressao=procedimento_exercicio.progressao,
            observacoes=observacoes,
            status=status,
        )
        _save_tracking_object(sessao_exercicio, changed=True)
    else:
        changed = False
        if _tracking_restore_needed(sessao_exercicio):
            changed = True
        sessao_exercicio.status = status
        changed = True
        if not sessao_exercicio.observacoes or sessao_exercicio.observacoes.startswith("Importacao:"):
            sessao_exercicio.observacoes = observacoes
            changed = True
        _save_tracking_object(sessao_exercicio, changed=changed)
    if context is not None:
        context.session_exercises[cache_key] = sessao_exercicio
    return sessao_exercicio


def _next_tracking_session_exercise_order(
    sessao: Sessao,
    context: TrackingImportSaveContext | None,
) -> int:
    if context is not None and sessao.pk in context.next_session_exercise_order:
        next_order = context.next_session_exercise_order[sessao.pk]
        context.next_session_exercise_order[sessao.pk] = next_order + 1
        return next_order

    next_order = (
        SessaoExercicio.all_objects.filter(sessao=sessao, is_active=True).aggregate(max_order=Max("ordem"))[
            "max_order"
        ]
        or 0
    ) + 1
    if context is not None:
        context.next_session_exercise_order[sessao.pk] = next_order + 1
    return next_order


def _tracking_mark_observation(marca: str, sheet_name: str, source_row: str) -> str:
    parts = [f"marca={marca}"]
    if sheet_name:
        parts.append(f"aba={sheet_name}")
    if source_row:
        parts.append(f"linha={source_row}")
    return "Importacao: " + "; ".join(parts)


def _tracking_session_status(performed_date: date) -> str:
    if performed_date <= timezone.localdate():
        return Sessao.STATUS_REALIZADA
    return Sessao.STATUS_AGENDADA


def _tracking_session_datetime(performed_date: date) -> datetime:
    return timezone.make_aware(datetime.combine(performed_date, time(hour=12)), timezone.get_current_timezone())


def _day_datetime_range(value: date) -> tuple[datetime, datetime]:
    current_timezone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(value, time.min), current_timezone),
        timezone.make_aware(datetime.combine(value, time.max), current_timezone),
    )


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
