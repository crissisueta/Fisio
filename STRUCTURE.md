# Estrutura do Projeto

## Estratégia atual

O projeto ainda mantém o app Django instalado como `forms` para preservar app label,
migrations, permissões e tabelas existentes. A organização interna, porém, foi
separada por domínio para reduzir acoplamento e facilitar uma futura migração para
apps Django independentes.

Os módulos legados `forms.models`, `forms.forms`, `forms.views` e `forms.services.*`
continuam existindo como camadas de compatibilidade.

## Árvore principal

```text
Fisio/
├── fisio_project/
│   ├── settings.py
│   └── urls.py
├── forms/
│   ├── core/
│   │   ├── admin.py
│   │   ├── mixins.py
│   │   ├── models.py
│   │   └── utils/datetime.py
│   ├── painel/
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── pacientes/
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── avaliacoes/
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── procedimentos/
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── presenters/calendar.py
│   │   ├── selectors.py
│   │   ├── services/
│   │   ├── urls.py
│   │   └── views/
│   ├── exercicios/
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── selectors.py
│   │   ├── services/
│   │   ├── urls.py
│   │   └── views.py
│   ├── migrations/
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
└── templates/
```

## Papéis dos módulos

- `models.py`: entidades e propriedades simples.
- `forms.py`: validação e widgets de entrada HTTP.
- `selectors.py`: consultas e composição de querysets.
- `services/`: regras de escrita e fluxos transacionais.
- `presenters/`: dados prontos para UI ou JSON sem acoplar views grandes.
- `views.py` / `views/`: autenticação, request/response, mensagens e redirects.
- `core/`: infraestrutura compartilhada, como soft delete, timestamps, mixins e utilitários.

## Compatibilidade

As URLs, nomes de rotas, templates, permissões `forms.*` e tabelas existentes foram
preservados. A próxima etapa estrutural deve ser mover cada domínio para apps Django
reais usando migrations de estado (`SeparateDatabaseAndState`) e `db_table` explícito.
