# TaskFlow API

API de gerenciamento de tarefas construída com **Python + FastAPI + SQLAlchemy + SQLite**.

Projeto didático com **arquitetura em camadas** (Router → Service → Repository → Model), foco em clareza, separação de responsabilidades e cobertura de testes.

---

## ✨ Features (MVP)

- CRUD de tarefas (criar, listar, buscar, atualizar, deletar via soft delete)
- Atalhos semânticos: `POST /tasks/{id}/complete`
- Estatísticas agregadas: `GET /tasks/stats`
- Filtros por status, prioridade e busca textual (case-insensitive)
- Paginação
- Transições de status validadas por máquina de estados
- Soft delete (`deleted_at`) — nada é apagado de verdade
- Documentação interativa via Swagger UI

---

## 🚀 Setup

### Pré-requisitos

- **Python 3.11+**
- Git (opcional, para controle de versão)

### Instalação

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente (opcional — tem defaults sensatos)
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
```

### Rodar a aplicação

```bash
python -m alembic upgrade head   # cria as tabelas no SQLite
python run.py                    # sobe o servidor com reload
```

A API estará disponível em:

- **Swagger UI**: <http://127.0.0.1:8000/docs>
- **ReDoc**: <http://127.0.0.1:8000/redoc>
- **OpenAPI JSON**: <http://127.0.0.1:8000/openapi.json>
- **Health**: <http://127.0.0.1:8000/health>

---

## 📂 Estrutura do projeto

```
taskflow-api/
├── app/
│   ├── core/              # Config (Settings) + database (engine, Session, Base, get_db)
│   ├── models/            # SQLAlchemy — Task, TaskStatus, TaskPriority
│   ├── schemas/           # Pydantic — TaskCreate, TaskUpdate, TaskRead, TaskStats, ...
│   ├── repositories/      # Única camada que fala com SQLAlchemy (CRUD + queries)
│   ├── services/          # Regras de negócio, transições, estatísticas
│   ├── routers/           # FastAPI — endpoints HTTP (health, tasks)
│   ├── exceptions.py      # TaskNotFoundError, InvalidStatusTransitionError
│   ├── main.py            # App FastAPI + handlers globais + lifespan
│   └── migrations/        # Alembic — versionamento de schema
├── tests/                 # Pytest — 21 testes, ~97% de cobertura
├── alembic.ini            # Config do Alembic
├── pytest.ini             # Config do Pytest + pytest-cov
├── pyproject.toml         # Config do ruff (linter/formatter)
├── requirements.txt       # Dependências fixadas
├── run.py                 # Atalho: python run.py
└── .env.example           # Exemplo de variáveis de ambiente
```

---

## 🏛️ Arquitetura

```
Cliente HTTP
   ↓
Router (FastAPI)             ← define endpoints, valida entrada
   ↓
Service (regras de negócio)  ← valida transições, calcula stats
   ↓
Repository (acesso a dados)  ← executa queries SQLAlchemy
   ↓
Model (ORM)                  ← mapeia tabela ``tasks``
   ↓
SQLite
```

**A dependência sempre flui para dentro.** Routers nunca importam SQLAlchemy, Services nunca retornam HTTPException.

---

## 🌐 Endpoints

| Método | Rota                          | Descrição                                |
|--------|-------------------------------|------------------------------------------|
| GET    | `/health`                     | Verifica se a API e o banco estão ok     |
| POST   | `/tasks`                      | Cria uma tarefa                          |
| GET    | `/tasks`                      | Lista tarefas (filtros + paginação)      |
| GET    | `/tasks/{task_id}`            | Busca tarefa por id                      |
| PATCH  | `/tasks/{task_id}`            | Atualiza parcialmente                    |
| DELETE | `/tasks/{task_id}`            | Soft delete                              |
| POST   | `/tasks/{task_id}/complete`   | Marca como concluída (idempotente)       |
| GET    | `/tasks/stats`                | Estatísticas agregadas                   |

---

## 🧪 Testes

```bash
# Rodar todos os testes com cobertura
pytest

# Rodar com cobertura detalhada
pytest --cov=app --cov-report=term-missing

# Rodar teste específico
pytest tests/test_tasks.py::test_create_task_returns_201_and_pending -v
```

Saída esperada:

```
============================= 21 passed in 0.7s ==============================
Coverage: 96%
```

---

## 🔧 Migrations (Alembic)

```bash
# Aplicar migrations pendentes
alembic upgrade head

# Criar nova migration após mudar um Model
alembic revision --autogenerate -m "descrição da mudança"

# Ver histórico
alembic history

# Reverter última migration
alembic downgrade -1
```

> O `lifespan` da aplicação **não** chama `Base.metadata.create_all()`. Toda mudança de schema passa por migrations.

---

## 🧹 Qualidade de código

```bash
# Lint + checagem de estilo
ruff check .

# Auto-correção do que for seguro
ruff check . --fix

# Formatação
ruff format .
```

---

## 📝 Exemplos curl

```bash
# Health check
curl http://127.0.0.1:8000/health

# Criar tarefa
curl -X POST http://127.0.0.1:8000/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "Estudar FastAPI", "priority": "high", "due_date": "2026-12-31T23:59:00Z"}'

# Listar tarefas pendentes
curl "http://127.0.0.1:8000/tasks?status=pending&page=1&page_size=20"

# Buscar tarefa por id
curl http://127.0.0.1:8000/tasks/1

# Atualizar (mudar status)
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
     -H "Content-Type: application/json" \
     -d '{"status": "in_progress"}'

# Marcar como concluída
curl -X POST http://127.0.0.1:8000/tasks/1/complete

# Estatísticas
curl http://127.0.0.1:8000/tasks/stats

# Soft delete
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

---

## 🗺️ Roadmap (não incluso no MVP)

- Autenticação de usuários (JWT)
- Categorias / tags
- Subtasks (relacionamento 1-N)
- Comentários
- Anexos / upload
- Notificações por e-mail para tarefas atrasadas
- WebSockets para atualizações em tempo real

---

## 📄 Licença

Projeto didático. Use à vontade.
