# TaskFlow API

API de gerenciamento de tarefas construída com **Python + FastAPI + SQLAlchemy + SQLite**.

---

## Stack

- **Linguagem:** Python (type hints obrigatórios em todo o código)
- **Framework web:** FastAPI
- **ORM:** SQLAlchemy
- **Banco de dados:** SQLite
- **Validação/Schemas:** Pydantic
- **Testes:** Pytest

---

## Arquitetura

Arquitetura em camadas com fluxo de dependência unidirecional:

```
Router → Service → Repository → Model
  (HTTP)   (regras)   (dados)     (ORM)
```

### Responsabilidades por camada

- **Router** (`app/routers/`): define endpoints HTTP, valida entrada via Pydantic, chama Services, retorna respostas. **Não acessa SQLAlchemy diretamente.**
- **Service** (`app/services/`): concentra **todas as regras de negócio**. Orquestra Repositories, valida transições de estado, calcula agregações. Não conhece HTTP.
- **Repository** (`app/repositories/`): **única camada que fala com SQLAlchemy**. CRUD, queries filtradas, paginação. Não tem regras de negócio.
- **Model** (`app/models/`): definição das tabelas, colunas, índices. Apenas mapeamento objeto-relacional.
- **Schema** (`app/schemas/`): DTOs Pydantic — contratos de entrada/saída da API.

A dependência sempre flui **para dentro**: Router depende de Service, Service depende de Repository, Repository depende de Model. Nunca o contrário.

---

## Padrões e Convenções

### Obrigatórios

- **Type hints em todo o código Python.**
- **Código, nomes de classes, funções, variáveis, arquivos e pastas em inglês.**
- **README e explicações/comentários em português** quando necessário.
- **Pydantic** para validação de entrada/saída e para configurações (settings).
- **Pytest** para todos os testes.

### Regras arquiteturais (não negociáveis)

1. Routers **nunca** importam SQLAlchemy ou acessam o banco diretamente.
2. Regras de negócio ficam **exclusivamente** nos Services.
3. Acesso ao banco (queries, CRUD) fica **exclusivamente** nos Repositories.
4. Toda nova funcionalidade deve ter **testes correspondentes**.
5. Após alterações relevantes, **executar os testes** antes de considerar a tarefa concluída.

### Dependências

- **Não adicionar dependências sem explicar o motivo.** Cada nova biblioteca precisa de justificativa clara (qual problema resolve, por que é necessária).
- Preferir bibliotecas do ecossistema padrão (FastAPI, SQLAlchemy, Pydantic, pytest) antes de buscar alternativas externas.

### Escopo

- **Não fazer alterações grandes fora do escopo solicitado.** Mudanças incrementais, cirúrgicas, com propósito claro.
- Desenvolver de forma **incremental**, commitando cada camada/funcionalidade separadamente quando possível.

---

## Estrutura de pastas (planejada)

```
taskflow-api/
├── app/
│   ├── core/           # config.py, database.py
│   ├── models/         # task.py
│   ├── schemas/        # task.py, common.py
│   ├── repositories/   # task_repository.py
│   ├── services/       # task_service.py
│   ├── routers/        # tasks.py, health.py
│   ├── exceptions.py
│   └── main.py
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md
```

---

## Fluxo de trabalho

1. Antes de implementar uma camada, **planejar** o que será feito.
2. Implementar a camada (ex.: Model).
3. Criar testes para a camada anterior (se aplicável) + a atual.
4. **Rodar `pytest`** após alterações relevantes.
5. Só considerar concluído quando os testes passam.
6. **Aguardar aprovação do usuário** antes de avançar para a próxima etapa.
