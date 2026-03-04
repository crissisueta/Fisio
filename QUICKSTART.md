# QUICK START - Sistema de Fichas de Fisioterapia

## Início Rápido (5 minutos)

### 1. Preparação Inicial

**Windows:**
```bash
python setup.py
```

**Linux/Mac:**
```bash
python3 setup.py
```

> O script setup.py irá:
> - Criar ambientes virtuais
> - Instalar dependências
> - Configurar banco de dados

---

### 2. Após o setup.py

**Windows:**
```bash
# Ativar ambiente virtual
venv\Scripts\activate

# Criar usuário admin
python manage.py createsuperuser
```

**Linux/Mac:**
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Criar usuário admin
python3 manage.py createsuperuser
```

> Quando solicitado, digite:
> - Username: `admin`
> - Email: seu email
> - Password: sua senha

---

### 3. Rodando a Aplicação

```bash
python manage.py runserver
```

Você verá:
```
Starting development server at http://127.0.0.1:8000/
```

---

### 4. Acessar a Aplicação

1. **Faça login** em http://localhost:8000/login/ com o usuário criado no passo anterior. Qualquer acesso às fichas ou URLs diretamente
   sem autenticação irá redirecionar você para essa página.
2. **Dashboard Principal**: http://localhost:8000 (após login)
3. **Painel Admin**: http://localhost:8000/admin
   - Login com as credenciais criadas

---

## Funcionalidades Disponíveis

### Dashboard
- Visualização de estatísticas de todas as fichas
- Atalhos rápidos para criar novas fichas

### Fichas de Avaliação

#### Inscrição
- Dados pessoais completos
- Contatos (telefone, celular, comercial)
- Informações de matrícula
- Plano de aulas

#### Anamnese Geral
- Histórico de saúde
- Condições médicas (diabetes, pressão alta, etc)
- Medicamentos em uso
- Queixas principais

#### Acupuntura
- Avaliação completa para acupuntura
- Histórico de saúde específico
- Exame de pulso e língua
- Diagnóstico e prescrição

#### Drenagem Linfática
- Dados antropométricos (altura, peso)
- Avaliação visual
- Histórico de saúde
- Queixas e sintomas

#### Exercícios
- Plano de exercícios personalizado
- Histórico patológico
- Avaliação de flexibilidade e força
- Acompanhamento

---

## Dicas de Uso

### Criar Nova Ficha
1. Clique em "Novo(a)" no menu
2. Preencha todos os campos obrigatórios
3. Clique em "Salvar"

### Editar Ficha Existente
2. Clique em "Ver" para visualizar
3. Clique em "Editar"
3. Modifique os dados
3. Clique em "Salvar"

### Deletar Ficha
1. Clique em "Deletar"
2. Confirme a ação
3. A ficha será removida permanentemente

### Pesquisar Fichas
- Use o painel Admin em http://localhost:8000/admin
- Há campos de busca e filtros em cada tipo de ficha

---

## Troubleshooting

### Erro: "python: command not found"
**Solução**: Use `python3` em vez de `python`

### Erro: "No module named 'django'"
**Solução**: Ativar ambiente virtual e rodar:
```bash
pip install -r requirements.txt
```

### Erro: "Address already in use"
**Solução**: Trocar porta:
```bash
python manage.py runserver 8001
```

### Erro: "No migrations"
**Solução**: Rodar:
```bash
python manage.py migrate
```

---

## Próximos Passos

1. Leia [README.md](README.md) para documentação completa
2. Explore o painel admin para gerenciar dados
3. Customize os formulários em `forms/forms.py`
4. Personalize os templates em `templates/`

---

## Precisa de Ajuda?

- Django Docs: https://docs.djangoproject.com/
- Python Docs: https://docs.python.org/3/
- Django Community: https://www.djangoproject.com/

---

**Versão**: 1.0  
**Última atualização**: Fevereiro de 2026
