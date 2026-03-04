# 📁 Estrutura do Projeto

Este documento descreve a estrutura completa da aplicação Django de Gestão de Fichas de Fisioterapia.

## Árvore de Diretórios

```
Fisio/
│
├── manage.py                           # Script de gerenciamento Django
├── setup.py                            # Script de configuração automática
├── requirements.txt                    # Dependências Python
├── README.md                           # Documentação principal
├── QUICKSTART.md                       # Guia de início rápido
├── STRUCTURE.md                        # Este arquivo
├── .gitignore                          # Arquivo Git ignorar
│
├── db.sqlite3                          # Banco de dados (criado após migrate)
│
├── fisio_project/                      # Configuração principal do projeto
│   ├── __init__.py
│   ├── settings.py                     # ⚙️ Configurações do Django
│   ├── urls.py                         # 🌐 URLs principais
│   └── wsgi.py                         # 🚀 WSGI para deploy
│
├── forms/                              # App principal de formulários
│   ├── __init__.py
│   ├── models.py                       # Modelos de banco de dados
│   ├── forms.py                        # Formulários Django
│   ├── views.py                        # Views e lógica
│   ├── urls.py                         # 🌐 URLs do app
│   ├── admin.py                        # ⚙️ Configuração admin
│   ├── apps.py                         # 📦 Configuração do app
│   └── migrations/                     # 🔄 Migrações do banco
│       ├── __init__.py
│       ├── 0001_initial.py
│       └── ...
│
├── templates/                          # Templates HTML
│   ├── base.html                       # Base template (layout principal)
│   ├── index.html                      # Dashboard
│   ├── 404.html                        # Página 404 (opcional)
│   ├── 500.html                        # Página 500 (opcional)
│   └── forms/                          # Templates dos formulários
│       ├── inscricao_list.html
│       ├── inscricao_form.html
│       ├── inscricao_detail.html
│       ├── inscricao_confirm_delete.html
│       ├── anamnese_geral_list.html
│       ├── anamnese_geral_form.html
│       ├── anamnese_geral_detail.html
│       ├── anamnese_geral_confirm_delete.html
│       ├── anamnese_acupuntura_list.html
│       ├── anamnese_acupuntura_form.html
│       ├── anamnese_acupuntura_detail.html
│       ├── anamnese_acupuntura_confirm_delete.html
│       ├── drenagem_list.html
│       ├── drenagem_form.html
│       ├── drenagem_detail.html
│       ├── drenagem_confirm_delete.html
│       ├── exercicios_list.html
│       ├── exercicios_form.html
│       ├── exercicios_detail.html
│       └── exercicios_confirm_delete.html
│
├── static/                             # 📦 Arquivos estáticos (CSS, JS, imagens)
│   ├── css/                            # Arquivos CSS customizados
│   ├── js/                             # Arquivos JavaScript customizados
│   └── images/                         # Imagens
│
└── venv/                               # Ambiente virtual (criado após setup)
    ├── bin/                            # Scripts executáveis
    ├── lib/                            # Pacotes Python instalados
    └── ...
```

## Modelos de Dados

### 1. FichaInscricao
```
- id (PrimaryKey)
- nome (CharField)
- cpf (CharField, unique)
- email (EmailField)
- endereco (CharField)
- bairro (CharField)
- cep (CharField)
- telefone (CharField)
- celular (CharField)
- telefone_comercial (CharField)
- data_nascimento (DateField)
- data_matricula (DateField)
- plano (CharField)
- observacoes (TextField)
- criado_em (DateTimeField, auto_now_add)
- atualizado_em (DateTimeField, auto_now)
```

### 2. AnamneseGeral
```
- id (PrimaryKey)
- nome (CharField)
- profissao (CharField)
- data_nascimento (DateField)
- data (DateField)
- diabetes (BooleanField)
- anemia (BooleanField)
- hipoglicemia (BooleanField)
- pressao_alta (BooleanField)
- pressao_baixa (BooleanField)
- problema_cardiaco (BooleanField)
- usa_medicamentos (BooleanField)
- medicamentos_quais (TextField)
- dor (TextField)
- observacoes (TextField)
- criado_em (DateTimeField, auto_now_add)
- atualizado_em (DateTimeField, auto_now)
```

### 3. AnamneseAcupuntura
```
- id (PrimaryKey)
- nome (CharField)
- data_consulta (DateField)
- endereco (CharField)
- telefone (CharField)
- data_nascimento (DateField)
- profissao (CharField)
- religiao (CharField)
- idade (IntegerField)
- estado_civil (CharField)
- filhos (CharField)
- ja_fez_acupuntura (BooleanField)
- queixa_principal (TextField)
- historia_doenca_atual (TextField)
- medicacao (TextField)
- historia_patologica_pregressa (TextField)
- doencas_familia (TextField)
- rotina_diaria (TextField)
- atividade_fisica (TextField)
- sono (TextField)
- emocao_predominante (CharField)
- sabor_preferido (CharField)
- pulso_direito (CharField)
- pulso_esquerdo (CharField)
- lingua (TextField)
- diagnostico (TextField)
- prescricao (TextField)
- observacoes (TextField)
- criado_em (DateTimeField, auto_now_add)
- atualizado_em (DateTimeField, auto_now)
```

### 4. FichaDrenagem
```
- id (PrimaryKey)
- nome (CharField)
- endereco (CharField)
- telefone (CharField)
- convenio (CharField)
- data_nascimento (DateField)
- idade (IntegerField)
- altura (DecimalField) - em cm
- peso (DecimalField) - em kg
- data (DateField)
- queixa (TextField)
- historia_doenca_atual (TextField)
- avaliacao (TextField)
- historia_patologica_pregressa (TextField)
- criado_em (DateTimeField, auto_now_add)
- atualizado_em (DateTimeField, auto_now)
```

### 5. FichaExercicios
```
- id (PrimaryKey)
- aluno (CharField)
- objetivo (TextField)
- historico_patologico (TextField)
- flexibilidade (TextField)
- dominancia_muscular (TextField)
- observacoes (TextField)
- dia (DateField)
- mes (CharField)
- criado_em (DateTimeField, auto_now_add)
- atualizado_em (DateTimeField, auto_now)
```

## 🌐 URLs e Rotas

### URLs Principais (`fisio_project/urls.py`)
```
/                           → Dashboard (DashboardView)
/admin/                     → Painel administrador Django
/forms/                     → URLs do app forms
```

### URLs do App Forms (`forms/urls.py`)

#### Fichas de Inscrição
```
/forms/inscricao/                    → Lista
/forms/inscricao/nova/               → Criar
/forms/inscricao/<id>/               → Detalhe
/forms/inscricao/<id>/editar/        → Editar
/forms/inscricao/<id>/deletar/       → Deletar
```

#### Anamnese Geral
```
/forms/anamnese-geral/                    → Lista
/forms/anamnese-geral/nova/               → Criar
/forms/anamnese-geral/<id>/               → Detalhe
/forms/anamnese-geral/<id>/editar/        → Editar
/forms/anamnese-geral/<id>/deletar/       → Deletar
```

#### Acupuntura
```
/forms/anamnese-acupuntura/                    → Lista
/forms/anamnese-acupuntura/nova/               → Criar
/forms/anamnese-acupuntura/<id>/               → Detalhe
/forms/anamnese-acupuntura/<id>/editar/        → Editar
/forms/anamnese-acupuntura/<id>/deletar/       → Deletar
```

#### Drenagem Linfática
```
/forms/drenagem/                    → Lista
/forms/drenagem/nova/               → Criar
/forms/drenagem/<id>/               → Detalhe
/forms/drenagem/<id>/editar/        → Editar
/forms/drenagem/<id>/deletar/       → Deletar
```

#### Exercícios
```
/forms/exercicios/                    → Lista
/forms/exercicios/novo/               → Criar
/forms/exercicios/<id>/               → Detalhe
/forms/exercicios/<id>/editar/        → Editar
/forms/exercicios/<id>/deletar/       → Deletar
```

## 🔄 Fluxo de Requisição

```
1. Usuario acessa URL
           ↓
2. fisio_project/urls.py roteia para forms/urls.py
           ↓
3. forms/urls.py roteia para view apropriada
           ↓
4. View (forms/views.py) processa a requisição
           ↓
5. View interage com Model (forms/models.py)
           ↓
6. Model retorna dados do banco (db.sqlite3)
           ↓
7. View renderiza template (templates/)
           ↓
8. Template retorna HTML ao navegador
```

## Formulários

Todos os formulários em `forms/forms.py` herdam de `forms.ModelForm`:

```python
class FichaInscricaoForm(forms.ModelForm)
class AnamneseGeralForm(forms.ModelForm)
class AnamneseAcupunturaForm(forms.ModelForm)
class FichaDrenagemForm(forms.ModelForm)
class FichaExerciciosForm(forms.ModelForm)
```

Cada formulário:
- Vincula-se a seu respectivo Model
- Define widgets Bootstrap para styling
- Valida dados automaticamente

## Views

Todas as views em `forms/views.py` usam Class-Based Views:

```python
DashboardView              → Exibe estatísticas
FichaInscricaoListView     → Lista fichas de inscrição
FichaInscricaoCreateView   → Cria nova ficha
FichaInscricaoDetailView   → Exibe detalhes
FichaInscricaoUpdateView   → Edita ficha
FichaInscricaoDeleteView   → Deleta ficha
# ... e há 4 conjuntos similares para os outros modelos
```

## Templates

Hierarquia de templates:
```
base.html (layout principal)
├── index.html (dashboard)
└── forms/
    ├── *_list.html (tabelas)
    ├── *_form.html (criar/editar)
    ├── *_detail.html (visualizar)
    └── *_confirm_delete.html (confirmar deleção)
```

## ⚙️ Configurações Importantes

### settings.py

- **INSTALLED_APPS**: `['forms', ...]`
- **TEMPLATES**: Configura diretório de templates
- **DATABASES**: SQLite3 padrão
- **LANGUAGE_CODE**: `pt-br`
- **TIME_ZONE**: `America/Sao_Paulo`
- **STATIC_URL**: `/static/`

### requirements.txt

```
Django==4.2.7
sqlparse==0.4.4
asgiref==3.7.1
```

## 🚀 Para Deploy em Produção

1. Alterar `DEBUG = False` em settings.py
2. Adicionar domínios em `ALLOWED_HOSTS`
3. Gerar nova `SECRET_KEY`
4. Usar banco de dados robusto (PostgreSQL)
5. Configurar HTTPS
6. Usar servidor production (Gunicorn)
7. Configurar servidor web (Nginx)

---

**Última atualização**: Fevereiro de 2026
