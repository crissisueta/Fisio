# Sistema de Gestão de Procedimentos de Fisioterapia

Aplicação Django para gestão de pacientes, procedimentos e sessões de acompanhamento em clínicas de fisioterapia.

## Arquitetura Atual

O sistema usa um modelo unificado:

- `FichaInscricao` (paciente)
- `ProcedureType` (tipo de procedimento)
- `Procedure` (plano/tratamento do paciente)
- `ProcedureSession` (sessões agendadas do procedimento)

Toda a agenda do calendário é baseada em `ProcedureSession`.

## Funcionalidades

- Cadastro e gestão de pacientes (`inscricao`)
- CRUD de procedimentos
- Múltiplas sessões por procedimento
- Marcação de status concluído/pendente em procedimento e sessão
- Calendário consolidado de sessões
- Django Admin para gestão completa

## Requisitos

- Python 3.8+
- pip

## Instalação

1. Entre na pasta do projeto:

```bash
cd /caminho/para/Fisio
```

2. Crie um ambiente virtual:

```bash
python -m venv .venv
```

3. Ative o ambiente virtual:

Linux/Mac:
```bash
source .venv/bin/activate
```

Windows:
```bash
.venv\Scripts\activate
```

4. Instale dependências:

```bash
pip install -r requirements.txt
```

5. Configure variáveis de ambiente (opcional para dev local):

- O projeto lê automaticamente `env/Fisio.env` se o arquivo existir.

6. Execute migrações:

```bash
python manage.py migrate
```

7. Crie um superusuário:

```bash
python manage.py createsuperuser
```

## Executar Aplicação

```bash
python manage.py runserver
```

Acessos:

- Dashboard: `http://localhost:8000/`
- Módulo de pacientes/procedimentos: `http://localhost:8000/forms/`
- Admin: `http://localhost:8000/admin`

## Estrutura Resumida

```text
Fisio/
├── fisio_project/               # Configuração Django
├── forms/                       # App principal
│   ├── models.py                # FichaInscricao, ProcedureType, Procedure, ProcedureSession
│   ├── views.py                 # Views de paciente/procedimento/sessão/calendário
│   ├── forms.py                 # ModelForms
│   ├── urls.py                  # Rotas do app
│   ├── admin.py                 # Configuração admin
│   └── migrations/              # Histórico de migrações (inclui migração de dados legados)
└── templates/
    ├── index.html
    ├── dashboard/calendar.html
    ├── includes/followup_section.html
    └── forms/
        ├── inscricao_*.html
        └── procedure_*.html
```

## Observação sobre Migração de Dados

As migrações recentes já incluem:

- criação do modelo unificado
- migração de dados legados para `Procedure`/`ProcedureSession`
- remoção dos modelos legados

Se você estiver em ambiente novo, apenas rode `migrate`.

## Suporte

- Django Docs: https://docs.djangoproject.com/
