# QUICK START - Sistema de Procedimentos de Fisioterapia

## Subir o projeto em 5 minutos

1. Criar e ativar ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Aplicar migrações:

```bash
python manage.py migrate
```

4. Criar usuário admin:

```bash
python manage.py createsuperuser
```

5. Iniciar servidor:

```bash
python manage.py runserver
```

## Rotas principais

- Login: `http://localhost:8000/login/`
- Dashboard: `http://localhost:8000/`
- Pacientes: `http://localhost:8000/forms/inscricao/`
- Procedimentos: `http://localhost:8000/forms/procedures/`
- Calendário: `http://localhost:8000/forms/calendar/`
- Admin: `http://localhost:8000/admin/`

## Fluxo recomendado de uso

1. Criar paciente em `Inscrição`
2. Criar tipo de procedimento no Admin (se necessário)
3. Criar procedimento vinculado ao paciente
4. Abrir detalhe do procedimento
5. Adicionar sessões (`+ Adicionar sessão`)
6. Acompanhar no calendário

## Troubleshooting rápido

- `python: command not found`:
  - use `python3`
- `No module named django`:
  - ative `.venv` e rode `pip install -r requirements.txt`
- Porta ocupada:
  - `python manage.py runserver 8001`
- Migração pendente:
  - `python manage.py migrate`
