# QUICK START - Sistema Clínico

## Subir em 5 minutos

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Rotas principais

- Login: `http://localhost:8000/login/`
- Painel: `http://localhost:8000/`
- Pacientes: `http://localhost:8000/forms/inscricao/`
- Avaliações: `http://localhost:8000/forms/avaliacoes/`
- Procedimentos: `http://localhost:8000/forms/procedimentos/`
- Calendário: `http://localhost:8000/forms/calendario/`

## Fluxo recomendado

1. Cadastrar paciente
2. Cadastrar tipos no Admin (`TipoAvaliacao` e `TipoProcedimento`) se necessário
3. Registrar avaliação
4. Criar procedimento
5. Adicionar sessões
6. Acompanhar agenda no calendário

## Problemas comuns

- `python: command not found`: usar `python3`
- `No module named django`: ativar `.venv` e instalar requisitos
- Porta ocupada: `python manage.py runserver 8001`
