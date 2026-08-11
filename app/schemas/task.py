"""Schemas Pydantic da entidade Task (entrada/saída da API)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import PaginatedResponse

# Constraints reutilizáveis — evita repetir regex/tamanhos nas classes.
TitleStr = Annotated[
    str, StringConstraints(min_length=1, max_length=120, strip_whitespace=True)
]
DescriptionStr = Annotated[
    str | None,
    StringConstraints(max_length=2000, strip_whitespace=True),
]


class TaskBase(BaseModel):
    """Campos comuns a Create/Update/Read."""

    title: TitleStr = Field(..., description="Título da tarefa (1-120 caracteres).")
    description: DescriptionStr = Field(
        default=None, description="Descrição opcional (até 2000 caracteres)."
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Prioridade: low | medium | high."
    )
    due_date: datetime | None = Field(
        default=None, description="Data limite (ISO 8601). Opcional."
    )


class TaskCreate(TaskBase):
    """Dados para criar uma tarefa.

    ``status`` não é aceito na criação — toda tarefa nasce como ``pending``.
    Para mudar o status, use PATCH ou /complete.
    """


class TaskUpdate(BaseModel):
    """Atualização parcial (PATCH) — todos os campos são opcionais.

    Apenas os campos enviados serão atualizados.
    """

    title: TitleStr | None = Field(default=None, min_length=1, max_length=120)
    description: DescriptionStr | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = Field(default=None)
    priority: TaskPriority | None = Field(default=None)
    due_date: datetime | None = Field(default=None)


class TaskRead(TaskBase):
    """Representação completa de uma tarefa retornada pela API."""

    id: int = Field(..., description="Identificador único.")
    status: TaskStatus = Field(..., description="Estado atual da tarefa.")
    created_at: datetime = Field(..., description="Data de criação.")
    updated_at: datetime = Field(..., description="Data da última atualização.")
    completed_at: datetime | None = Field(
        default=None, description="Data de conclusão (preenchida quando status=completed)."
    )

    model_config = ConfigDict(from_attributes=True)


class TaskStats(BaseModel):
    """Estatísticas agregadas das tarefas."""

    total: int = Field(..., ge=0, description="Total de tarefas não removidas.")
    pending: int = Field(..., ge=0, description="Tarefas com status=pending.")
    in_progress: int = Field(..., ge=0, description="Tarefas com status=in_progress.")
    completed: int = Field(..., ge=0, description="Tarefas com status=completed.")
    overdue: int = Field(
        ...,
        ge=0,
        description="Tarefas não concluídas com due_date no passado.",
    )


class TaskFilters(BaseModel):
    """Filtros aceitos em GET /tasks."""

    status: TaskStatus | None = Field(default=None)
    priority: TaskPriority | None = Field(default=None)
    search: Annotated[
        str | None,
        StringConstraints(min_length=1, max_length=120, strip_whitespace=True),
    ] = Field(default=None, description="Busca por título (LIKE case-insensitive).")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")


# Alias semântico: ``PaginatedResponse[TaskRead]`` é o tipo de retorno de
# ``GET /tasks``. Em tempo de execução Pydantic resolve corretamente.
TaskListResponse = PaginatedResponse[TaskRead]
