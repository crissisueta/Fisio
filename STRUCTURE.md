# Estrutura do Projeto

## Árvore principal

```text
Fisio/
├── fisio_project/
├── forms/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── services/calendar_service.py
│   └── migrations/
└── templates/
    ├── base.html
    ├── index.html
    ├── dashboard/calendar.html
    ├── includes/followup_section.html
    └── forms/
        ├── inscricao_*.html
        ├── avaliacao_*.html
        └── procedure_*.html
```

## Modelos atuais

### `Paciente`
Dados cadastrais e clínicos básicos do paciente.

### `TipoAvaliacao`
Catálogo de tipos de avaliação.

### `Avaliacao`
Registro de avaliação não recorrente.

Campos principais:
- `paciente`
- `tipo_avaliacao`
- `data_hora`
- `concluida`
- `observacoes`

### `TipoProcedimento`
Catálogo de tipos de procedimento terapêutico.

### `Procedimento`
Plano terapêutico do paciente.

Campos principais:
- `paciente`
- `tipo_procedimento`
- `concluido`
- `observacoes`

### `Sessao`
Atendimento/sessão vinculada ao procedimento.

Campos principais:
- `procedimento`
- `data_hora`
- `numero`
- `status` (`agendada`, `realizada`, `faltou`, `cancelada`)
- `assinatura_confirmada`
- `observacoes`

### `FichaExercicios` (base para evolução futura)
Estrutura inicial para planejamento de exercícios, sem lógica avançada nesta etapa.

Campos principais:
- `paciente`
- `procedimento` (opcional)
- `titulo`
- `observacoes`
- `ativo`

## URLs do app (`forms/urls.py`)

- Pacientes: `/forms/inscricao/...`
- Avaliações: `/forms/avaliacoes/...`
- Procedimentos: `/forms/procedimentos/...`
- Sessões: `/forms/sessoes/...`
- Calendário: `/forms/calendario/` e `/forms/calendario/eventos/`

## Calendário

`forms/services/calendar_service.py` consulta somente `Sessao`.

Cada evento contém:
- paciente + tipo de procedimento
- data/hora da sessão
- cor do evento pelo tipo de procedimento
- ponto visual indicando se o procedimento está concluído
