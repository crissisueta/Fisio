# Estrutura do Projeto

## Árvore principal

```text
Fisio/
├── manage.py
├── requirements.txt
├── README.md
├── QUICKSTART.md
├── STRUCTURE.md
├── fisio_project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── forms/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── services/
│   │   └── calendar_service.py
│   └── migrations/
└── templates/
    ├── base.html
    ├── index.html
    ├── dashboard/
    │   └── calendar.html
    ├── includes/
    │   └── followup_section.html
    └── forms/
        ├── inscricao_list.html
        ├── inscricao_form.html
        ├── inscricao_detail.html
        ├── inscricao_confirm_delete.html
        ├── procedure_list.html
        ├── procedure_form.html
        ├── procedure_detail.html
        └── procedure_confirm_delete.html
```

## Modelos atuais (`forms/models.py`)

### `FichaInscricao`
Paciente da clínica.

Campos principais:
- `nome`, `cpf`, `email`
- `profissao`
- `endereco`, `bairro`, `cep`
- `telefone`, `celular`, `telefone_comercial`
- `data_nascimento`, `data_matricula`
- `plano`, `observacoes`
- `created_at`, `updated_at`

### `ProcedureType`
Catálogo de tipos de procedimento.

Campos:
- `name`

### `Procedure`
Tratamento de um paciente.

Campos:
- `patient` (`FK -> FichaInscricao`)
- `procedure_type` (`FK -> ProcedureType`)
- `observacoes`
- `is_complete`
- `created_at`, `updated_at`

### `ProcedureSession`
Sessões de acompanhamento de cada procedimento.

Campos:
- `procedure` (`FK -> Procedure`)
- `scheduled_datetime`
- `notes`
- `completed`
- `created_at`, `updated_at`

## URLs principais

### `fisio_project/urls.py`
- `/` dashboard
- `/admin/`
- `/login/`, `/logout/`
- `/forms/` inclui URLs do app

### `forms/urls.py`
- Pacientes:
  - `/forms/inscricao/`
  - `/forms/inscricao/nova/`
  - `/forms/inscricao/<id>/`
  - `/forms/inscricao/<id>/editar/`
  - `/forms/inscricao/<id>/deletar/`
- Procedimentos:
  - `/forms/procedures/`
  - `/forms/procedures/novo/`
  - `/forms/procedures/<id>/`
  - `/forms/procedures/<id>/editar/`
  - `/forms/procedures/<id>/deletar/`
  - `/forms/procedures/<id>/toggle-complete/`
- Sessões:
  - `/forms/procedures/<id>/sessions/new/`
  - `/forms/sessions/<id>/edit/`
- Calendário:
  - `/forms/calendar/`
  - `/forms/calendar/events/`

## Calendário

`forms/services/calendar_service.py` gera eventos exclusivamente de `ProcedureSession`.

- título: paciente + tipo de procedimento
- data/hora: `scheduled_datetime`
- cor:
  - verde: sessão concluída
  - amarelo: sessão pendente
