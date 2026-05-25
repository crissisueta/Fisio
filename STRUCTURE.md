# Estrutura do Projeto

O projeto agora segue o layout convencional criado por `django-admin startproject`
e `python manage.py startapp`: `manage.py` na raiz, o pacote de configuração em
`fisio_project/` e cada domínio como um app Django de primeiro nível.

```text
Fisio/
├── manage.py
├── fisio_project/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/
├── painel/
├── pacientes/
├── avaliacoes/
├── procedimentos/
├── exercicios/
├── forms/
├── templates/
├── static/
├── requirements.txt
├── Procfile
└── .env.example
```

## Apps

- `core`: mixins, models abstratos e utilitários compartilhados.
- `painel`: dashboard inicial.
- `pacientes`: cadastro e API de paciente.
- `avaliacoes`: tipos de avaliação e avaliações clínicas.
- `procedimentos`: tipos de procedimento, procedimentos, sessões e calendário.
- `exercicios`: catálogo, categorias e controle de exercícios.
- `forms`: camada de compatibilidade para imports legados e agregação das URLs sob `/forms/`.

## Compatibilidade

As rotas e nomes de URL foram preservados. As tabelas existentes também foram
preservadas com `db_table` explícito nos novos apps, mantendo nomes como
`forms_paciente`, `forms_procedimento` e `forms_sessao`.

As migrações antigas do app único foram movidas para `forms_legacy_migrations/`
como referência histórica. Elas não são carregadas pelo Django. As migrações
ativas vivem nos apps reais: `pacientes`, `avaliacoes`, `procedimentos` e
`exercicios`.
