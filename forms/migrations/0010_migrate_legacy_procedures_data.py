from django.db import migrations
from django.utils import timezone


def _ensure_aware(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _first_or_create_type(ProcedureType, name):
    instance = ProcedureType.objects.filter(name=name).first()
    if instance:
        return instance
    return ProcedureType.objects.create(name=name)


def _build_placeholder_patient(FichaInscricao, name, seed):
    generated_cpf = str(90000000000000 + seed)[-14:]
    patient, _ = FichaInscricao.objects.get_or_create(
        cpf=generated_cpf,
        defaults={
            "nome": name or f"Paciente Migrado {seed}",
            "email": f"migrado+{seed}@example.local",
            "profissao": "",
            "endereco": "Endereço não informado",
            "bairro": "Não informado",
            "cep": "00000-000",
            "telefone": "",
            "celular": "00000000000",
            "telefone_comercial": "",
            "data_nascimento": timezone.now().date(),
            "data_matricula": timezone.now().date(),
            "plano": "Não informado",
            "observacoes": "Paciente criado automaticamente para migração de procedimento legado.",
        },
    )
    return patient


def _resolve_patient(record, FichaInscricao, seed):
    patient_id = getattr(record, "paciente_id", None)
    if patient_id:
        patient = FichaInscricao.objects.filter(pk=patient_id).first()
        if patient:
            return patient

    name = getattr(record, "nome", "") or getattr(record, "aluno", "") or "Paciente sem nome"
    by_name = FichaInscricao.objects.filter(nome=name).order_by("id").first()
    if by_name:
        return by_name

    return _build_placeholder_patient(FichaInscricao, name, seed)


def _create_procedure_and_initial_session(
    Procedure,
    ProcedureSession,
    FichaInscricao,
    record,
    procedure_type,
    when,
    notes,
    is_complete,
    seed,
):
    patient = _resolve_patient(record, FichaInscricao, seed)
    created_at = _ensure_aware(getattr(record, "created_at", timezone.now()))

    procedure = Procedure.objects.create(
        patient=patient,
        procedure_type=procedure_type,
        observacoes=notes,
        is_complete=is_complete,
        created_at=created_at,
    )

    if when:
        ProcedureSession.objects.create(
            procedure=procedure,
            scheduled_datetime=_ensure_aware(when),
            notes=notes,
            completed=is_complete,
            created_at=created_at,
        )

    return procedure


def migrate_legacy_data(apps, schema_editor):
    FichaInscricao = apps.get_model("forms", "FichaInscricao")
    ProcedureType = apps.get_model("forms", "ProcedureType")
    Procedure = apps.get_model("forms", "Procedure")
    ProcedureSession = apps.get_model("forms", "ProcedureSession")

    AnamneseGeral = apps.get_model("forms", "AnamneseGeral")
    AnamneseAcupuntura = apps.get_model("forms", "AnamneseAcupuntura")
    FichaDrenagem = apps.get_model("forms", "FichaDrenagem")
    FichaExercicios = apps.get_model("forms", "FichaExercicios")
    FollowUpSession = apps.get_model("forms", "FollowUpSession")

    type_map = {
        "anamnesegeral": _first_or_create_type(ProcedureType, "Anamnese Geral"),
        "anamneseacupuntura": _first_or_create_type(ProcedureType, "Acupuntura"),
        "fichadrenagem": _first_or_create_type(ProcedureType, "Drenagem Linfática"),
        "fichaexercicios": _first_or_create_type(ProcedureType, "Exercícios"),
    }

    legacy_to_new = {}

    for record in AnamneseGeral.objects.all().iterator():
        notes = record.observacoes or ""
        procedure = _create_procedure_and_initial_session(
            Procedure,
            ProcedureSession,
            FichaInscricao,
            record,
            type_map["anamnesegeral"],
            record.data,
            notes,
            bool(getattr(record, "concluido", False)),
            100000 + record.pk,
        )
        legacy_to_new[("anamnesegeral", record.pk)] = procedure.pk

    for record in AnamneseAcupuntura.objects.all().iterator():
        notes = record.observacoes or record.queixa_principal or ""
        procedure = _create_procedure_and_initial_session(
            Procedure,
            ProcedureSession,
            FichaInscricao,
            record,
            type_map["anamneseacupuntura"],
            record.data_consulta,
            notes,
            bool(getattr(record, "concluido", False)),
            200000 + record.pk,
        )
        legacy_to_new[("anamneseacupuntura", record.pk)] = procedure.pk

    for record in FichaDrenagem.objects.all().iterator():
        notes_parts = [value for value in [record.avaliacao, record.queixa, record.historia_doenca_atual] if value]
        notes = "\n\n".join(notes_parts)
        procedure = _create_procedure_and_initial_session(
            Procedure,
            ProcedureSession,
            FichaInscricao,
            record,
            type_map["fichadrenagem"],
            record.data,
            notes,
            bool(getattr(record, "concluido", False)),
            300000 + record.pk,
        )
        legacy_to_new[("fichadrenagem", record.pk)] = procedure.pk

    for record in FichaExercicios.objects.all().iterator():
        notes_parts = [value for value in [record.observacoes, record.objetivo, record.historico_patologico] if value]
        notes = "\n\n".join(notes_parts)
        procedure = _create_procedure_and_initial_session(
            Procedure,
            ProcedureSession,
            FichaInscricao,
            record,
            type_map["fichaexercicios"],
            record.dia,
            notes,
            bool(getattr(record, "concluido", False)),
            400000 + record.pk,
        )
        legacy_to_new[("fichaexercicios", record.pk)] = procedure.pk

    for followup in FollowUpSession.objects.select_related("content_type").all().iterator():
        model_key = followup.content_type.model
        procedure_id = legacy_to_new.get((model_key, followup.object_id))
        if not procedure_id:
            continue

        ProcedureSession.objects.create(
            procedure_id=procedure_id,
            scheduled_datetime=_ensure_aware(followup.session_date),
            notes=followup.notes or "",
            completed=False,
            created_at=_ensure_aware(followup.created_at),
        )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0009_add_updated_at_to_procedure_models"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_data, noop_reverse),
    ]
