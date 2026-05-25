# Sistema de Gestão Clínica de Fisioterapia

Aplicação Django para gestão de pacientes, avaliações, procedimentos e sessões de acompanhamento.

## Arquitetura

Layout Django convencional:

- `manage.py` na raiz do projeto.
- `fisio_project/` para `settings.py`, `urls.py`, `wsgi.py` e `asgi.py`.
- Apps Django separados: `pacientes`, `avaliacoes`, `procedimentos`, `exercicios`, `painel` e `core`.
- `forms/` permanece apenas como compatibilidade para imports legados e para manter as URLs sob `/forms/`.

Modelos principais:

- `Paciente`
- `TipoAvaliacao`
- `Avaliacao`
- `TipoProcedimento`
- `Procedimento`
- `Sessao`
- `FichaExercicios` (estrutura base, sem módulo avançado nesta fase)

Calendário: gera eventos somente a partir de `Sessao`.

## Funcionalidades

- Cadastro completo de pacientes
- Cadastro de tipos de avaliação e de procedimento
- Registro de avaliações clínicas
- Gestão de procedimentos terapêuticos
- Sessões com status: `agendada`, `realizada`, `faltou`, `cancelada`
- Linha do tempo de sessões por procedimento
- Calendário com cor por tipo de procedimento e indicador visual de conclusão do procedimento

## Requisitos

- Python 3.8+
- pip

## Instalação

```bash
cd /caminho/para/Fisio
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Acessos

- Painel: `http://localhost:8000/`
- Pacientes: `http://localhost:8000/forms/inscricao/`
- Avaliações: `http://localhost:8000/forms/avaliacoes/`
- Procedimentos: `http://localhost:8000/forms/procedimentos/`
- Calendário: `http://localhost:8000/forms/calendario/`
- Admin: `http://localhost:8000/admin/`

## Observações da Migração

Os novos apps usam `db_table` explícito para preservar as tabelas históricas
`forms_*`. As migrações antigas do app único ficam em `forms_legacy_migrations/`
somente como referência.

## Suporte

- Django Docs: https://docs.djangoproject.com/
