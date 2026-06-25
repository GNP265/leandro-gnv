# Leandro GNV — Sistema de Gestão de OS

Sistema web completo para gestão de ordens de serviço de loja instaladora de GNV.

## Como colocar no ar (passo a passo)

### Passo 1: Criar conta no GitHub (se não tiver)

1. Acesse **github.com** e clique em **"Sign up"**
2. Crie sua conta com email e senha
3. Confirme o email

### Passo 2: Criar repositório e subir os arquivos

1. No GitHub, clique no **"+"** no canto superior direito → **"New repository"**
2. Nome: `leandro-gnv`
3. Marque **"Public"** (obrigatório para Railway grátis)
4. Clique em **"Create repository"**
5. Na página do repositório, clique em **"uploading an existing file"**
6. Descompacte o `.zip` e arraste **TODAS as pastas e arquivos** para a área de upload
7. Clique em **"Commit changes"**

### Passo 3: Deploy no Railway

1. Acesse **railway.app** e clique em **"Login"** → **"GitHub"**
2. Autorize o Railway a acessar seu GitHub
3. Clique em **"New Project"** → **"Deploy from GitHub Repo"**
4. Selecione o repositório `leandro-gnv`
5. Railway vai detectar automaticamente que é Python/Django
6. Aguarde ~2 minutos para o deploy completar

### Passo 4: Configurar variáveis de ambiente

No Railway, vá em **Settings** → **Variables** e adicione:

```
SECRET_KEY = uma-chave-secreta-longa-aleatoria-123456
DEBUG = False
ALLOWED_HOSTS = *
CSRF_TRUSTED_ORIGINS = https://SEU-DOMINIO.up.railway.app
```

### Passo 5: Criar o primeiro usuário

No Railway, vá em **Deployments** → clique nos 3 pontos → **"Shell"** e execute:

```bash
python manage.py migrate
python create_admin.py
```

Isso cria o usuário **leandro** com senha **gnv2024**.

**⚠️ IMPORTANTE: Troque a senha pelo painel /admin/ após o primeiro login!**

### Passo 6: Acessar o sistema

O Railway gera automaticamente uma URL tipo:
`https://leandro-gnv-production.up.railway.app`

Clique nela e faça login com as credenciais criadas.

---

## Funcionalidades

- **Dashboard** — faturamento, lucro, custo de materiais, últimas OS
- **Ordens de Serviço** — CRUD completo com busca, filtros e checklist GNV
- **Clientes** — gerados automaticamente a partir das OS
- **Financeiro** — relatórios por mês, trimestre ou tudo
- **Colaboradores** — cadastro + comissões por semana/mês/trimestre/ano
- **Exportar CSV** — backup completo em planilha
- **Login e senha** — acesso protegido
- **Responsivo** — funciona no celular

## Tecnologias

- Python 3.11 + Django 4.2
- SQLite (local) ou PostgreSQL (produção)
- Gunicorn + WhiteNoise
- Railway (hospedagem gratuita)
