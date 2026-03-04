# Sistema de Gestão de Fichas de Fisioterapia

Uma aplicação Django para gerenciar formulários e fichas de avaliação em clínicas de fisioterapia.

## Funcionalidades

- **Ficha de Inscrição**: Registro de novos pacientes
- **Anamnese Geral**: Histórico geral de saúde
- **Anamnese Acupuntura**: Avaliação específica para acupuntura
- **Drenagem Linfática**: Avaliação de drenagem linfática
- **Ficha de Exercícios**: Planejamento de exercícios personalizados

## Requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## Instalação

### 1. Clone ou extraia o projeto

```bash
cd /caminho/para/Fisio
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

**No Linux/Mac:**
```bash
source venv/bin/activate
```

**No Windows:**
```bash
venv\Scripts\activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Execute as migrações do banco de dados

```bash
python manage.py migrate
```

### 6. Crie um usuário admin (superuser)

```bash
python manage.py createsuperuser
```

Você será solicitado a informar:
- Nome de usuário
- Email
- Senha
- Confirmar senha

## Rodando a Aplicação

### 1. Inicie o servidor de desenvolvimento

```bash
python manage.py runserver
```

### 2. Acesse a aplicação

Abra seu navegador e vá para:
- **Dashboard**: http://localhost:8000
- **Admin**: http://localhost:8000/admin

## Estrutura do Projeto

```
Fisio/
├── manage.py                           # Arquivo de gerenciamento Django
├── requirements.txt                    # Dependências do projeto
├── db.sqlite3                         # Banco de dados (criado automaticamente)
├── fisio_project/                     # Configuração do projeto
│   ├── settings.py                    # Configurações do Django
│   ├── urls.py                        # URLs principais
│   └── wsgi.py                        # Arquivo WSGI
├── forms/                             # App principal
│   ├── models.py                      # Modelos de banco de dados
│   ├── forms.py                       # Formulários Django
│   ├── views.py                       # Views
│   ├── urls.py                        # URLs do app
│   └── admin.py                       # Configuração do admin
└── templates/                         # Templates HTML
    ├── base.html                      # Template base
    ├── index.html                     # Dashboard
    └── forms/                         # Templates dos formulários
```

## Modelos de Dados

### FichaInscricao
Informações básicas de inscrição do paciente

### AnamneseGeral
Histórico geral de saúde e condições médicas

### AnamneseAcupuntura
Avaliação específica para tratamento de acupuntura

### FichaDrenagem
Avaliação para tratamento de drenagem linfática

### FichaExercicios
Planejamento e acompanhamento de exercícios

## Acessando o Admin Panel

1. Vá para http://localhost:8000/admin
2. Faça login com as credenciais de superuser criadas
3. Gerenciadores todas as fichas diretamente na interface de administração

## Recursos Adicionais

- **Bootstrap 5**: Interface responsiva e moderna
- **SQLite**: Banco de dados leve (padrão)
- **Django Admin**: Interface administrativa completa
- **CRUD Completo**: Create, Read, Update, Delete para cada tipo de ficha

## Dicas de Uso

- Use o dashboard para uma visão geral rápida de todas as fichas
- Os formulários validam automaticamente os dados antes de salvar
- Todas as fichas possuem histórico de criação e atualização
- Você pode pesquisar e filtrar fichas no painel admin

## Suporte

Para problemas ou dúvidas, consulte a documentação oficial do Django em https://www.djangoproject.com/

---

**Versão**: 1.0
**Data**: Fevereiro de 2026
