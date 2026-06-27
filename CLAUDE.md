# CLAUDE.md — Divisor de Contas (Split)

## O que é este projeto

App mobile-first para **divisão de contas em grupo** (restaurantes, bares, viagens). Permite cadastrar pessoas, adicionar itens com preço e quantidade, e atribuir cada item (ou quantidade individual) para quem consumiu — com cálculo automático de gorjeta por pessoa.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | HTML/CSS/JS puro — single page, sem framework |
| Backend | FastAPI (Python) |
| Banco | PostgreSQL (Railway em produção, local para dev) |
| Deploy | GitHub → Railway (auto-deploy na main) |
| Auth | Email + senha com verificação por e-mail (token JWT) |

---

## Como rodar localmente

```bash
cd "/Users/sm4x/Library/Mobile Documents/com~apple~CloudDocs/10. Dados/06_split"

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (abre direto no browser)
open backend/frontend/index.html
```

Banco local: variável `DATABASE_URL` no `.env` (PostgreSQL local ou SQLite para dev rápido).

---

## Estrutura do projeto

```
06_split/
  CLAUDE.md
  backend/
    frontend/
      index.html       # App principal (mobile-first, single HTML)
      admin.html        # Painel administrativo
    app/
      main.py           # FastAPI entry point, CORS, monta routers, serve frontend/
      database.py       # SQLAlchemy engine + get_db() + Base
      models.py         # Tabelas ORM (users, sessoes, itens, atribuicoes)
      schemas.py        # Pydantic schemas (request/response)
      auth.py           # JWT, hash de senha, envio de e-mail de verificação
      routers/
        auth.py         # POST /auth/register, /auth/login, /auth/verify-email
        sessoes.py      # CRUD de sessões de divisão
        itens.py        # CRUD de itens + atribuições individuais
    requirements.txt
    railway.toml
    .env.example
```

**Importante:** o frontend vive só em `backend/frontend/` — não duplicar em
outro lugar do repo. O Root Directory do serviço no Railway é `backend`, então
qualquer pasta `frontend/` fora dali não entra no build e nunca é servida em
produção (foi a causa de um bug em que correções no frontend não apareciam
no app publicado).

---

## Deploy (Railway + GitHub)

1. Repositório GitHub: `sm4x/06_split`
2. Railway conectado ao repo — auto-deploy em push na `main`
3. Variáveis de ambiente no Railway:
   - `DATABASE_URL` — PostgreSQL provisionado pelo Railway
   - `SECRET_KEY` — chave JWT
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` — envio de e-mail
   - `FRONTEND_URL` — URL do frontend para links de verificação

`railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
```

---

## Banco de dados — tabelas principais

| Tabela | Descrição |
|---|---|
| `users` | Usuários cadastrados (email, senha hash, verificado, criado_em) |
| `email_tokens` | Tokens de verificação de e-mail (token, user_id, expira_em) |
| `sessoes` | Cada "conta" a dividir (nome, criado por, data) |
| `pessoas` | Participantes de uma sessão (nome, emoji, cor) |
| `itens` | Itens de uma sessão (nome, emoji, preço unitário, quantidade total) |
| `atribuicoes` | Quem consumiu o quê — **quantidade por pessoa por item** (item_id, pessoa_id, qtd) |

### Lógica de atribuição

- **Modo grupo (igual):** `atribuicoes` com mesma `qtd` para todos os atribuídos (dividido no cálculo)
- **Modo individual:** `atribuicoes` com `qtd` específica por pessoa (ex: João=2, Maria=1 de 3 cervejas)
- Custo por pessoa por item: `preco_unitario × atribuicao.qtd`

---

## Auth — fluxo de cadastro

1. `POST /auth/register` — cria user com `verificado=false`, envia e-mail com token (24h)
2. `GET /auth/verify-email?token=xxx` — marca `verificado=true`
3. `POST /auth/login` — retorna JWT (30 dias) se verificado
4. Frontend guarda JWT no `localStorage`, envia em `Authorization: Bearer <token>`

---

## Frontend — funcionalidades

### Existentes (manter)
- Cadastro de pessoas com emoji + cor
- Adição de itens (nome, emoji, preço, quantidade)
- **Drag-and-drop** de item para pessoa (atribuição igual entre os atribuídos)
- Modo Grupo: seleciona várias pessoas e arrasta para dividir igualmente
- Gorjeta configurável (0%, 10%, 12%, 15% ou custom)
- Resumo por pessoa com detalhamento de itens

### Novas (a implementar)
- **Login/cadastro** com tela inicial se não autenticado
- **Itens individuais com quantidade por pessoa:** toque no item → modal com lista de pessoas + stepper de quantidade para cada uma
- Sessões salvas no backend (persistência entre dispositivos)
- Pessoas favoritas salvas na conta do usuário

---

## Padrões do projeto

- Backend: sempre tipar com Pydantic; usar `Depends(get_db)` e `Depends(get_current_user)`
- Datas: `TIMESTAMP WITH TIME ZONE` no Postgres
- Senhas: `bcrypt` via `passlib`
- JWT: `python-jose`
- CORS: permitir origem do frontend em produção + `localhost` em dev
- Frontend: sem frameworks externos além de Tabler Icons (CDN); CSS em `<style>` inline
- Valores monetários: `NUMERIC(10,2)` no banco, `float` no Python, formatado `R$ X,XX` no frontend
