"""Endpoints HTTP da entidade Task.

Routers NUNCA importam SQLAlchemy. Eles só:
    1. Validam entrada via Pydantic (``Query``, ``Body``).
    2. Chamam o Service.
    3. Traduzem o resultado para o schema de saída.

Erros de domínio são traduzidos por handlers globais em ``main.py``.

IMPORTANTE — ordem das rotas:
    O endpoint estático ``GET /tasks/stats`` precisa estar registrado
    ANTES de ``GET /tasks/{task_id}``. Caso contrário, o FastAPI
    roteia ``/tasks/stats`` para a rota dinâmica ``/{task_id}``
    e tenta parsear "stats" como int (gerando 422).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import (
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskRead,
    TaskStats,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_service(db: Session = Depends(get_db)) -> TaskService:
    """Fábrica de Service injetada por request.

    Encapsula a criação do Repository — o router NUNCA instancia
    o Repository diretamente.
    """
    return TaskService(TaskRepository(db))


# ----------------------------------------------------------------------
# STATS  (registrada antes da rota dinâmica /{task_id})
# ----------------------------------------------------------------------
@router.get(
    "/stats",
    response_model=TaskStats,
    summary="Estatísticas agregadas das tarefas",
)
def get_stats(
    service: TaskService = Depends(_get_service),
) -> TaskStats:
    """Total, contagem por status e tarefas atrasadas."""
    return service.get_stats()


# ----------------------------------------------------------------------
# CREATE
# ----------------------------------------------------------------------
@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova tarefa",
)
def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(_get_service),
) -> TaskRead:
    """Cria tarefa. Sempre nasce em status=pending."""
    task = service.create_task(payload)
    return TaskRead.model_validate(task)


# ----------------------------------------------------------------------
# LIST
# ----------------------------------------------------------------------
@router.get(
    "",
    response_model=TaskListResponse,
    summary="Lista tarefas com filtros e paginação",
)
def list_tasks(
    status: TaskStatus | None = Query(default=None, description="Filtra por status."),
    priority: TaskPriority | None = Query(default=None, description="Filtra por prioridade."),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description="Busca por título ou descrição.",
    ),
    page: int = Query(default=1, ge=1, description="Número da página."),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página."),
    service: TaskService = Depends(_get_service),
) -> TaskListResponse:
    """Lista tarefas não removidas, ordenadas das mais recentes para as mais antigas."""
    filters = TaskFilters(
        status=status,
        priority=priority,
        search=search,
        page=page,
        page_size=page_size,
    )
    items, total = service.list_tasks(filters)
    return TaskListResponse(
        items=[TaskRead.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ----------------------------------------------------------------------
# READ by id
# ----------------------------------------------------------------------
@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Busca uma tarefa por id",
)
def get_task(
    task_id: int = Path(..., ge=1, description="Identificador da tarefa."),
    service: TaskService = Depends(_get_service),
) -> TaskRead:
    """Retorna 404 (via handler global) se a tarefa não existir."""
    task = service.get_task(task_id)
    return TaskRead.model_validate(task)


# ----------------------------------------------------------------------
# UPDATE (parcial)
# ----------------------------------------------------------------------
@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    summary="Atualiza uma tarefa (parcial)",
)
def patch_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskService = Depends(_get_service),
) -> TaskRead:
    """Atualiza apenas os campos enviados. Valida transição de status."""
    task = service.update_task(task_id, payload)
    return TaskRead.model_validate(task)


# ----------------------------------------------------------------------
# COMPLETE (atalho semântico)
# ----------------------------------------------------------------------
@router.post(
    "/{task_id}/complete",
    response_model=TaskRead,
    summary="Marca a tarefa como concluída",
)
def complete_task(
    task_id: int = Path(..., ge=1),
    service: TaskService = Depends(_get_service),
) -> TaskRead:
    """Idempotente: se já está concluída, retorna o estado atual."""
    task = service.complete_task(task_id)
    return TaskRead.model_validate(task)


# ----------------------------------------------------------------------
# DELETE (soft)
# ----------------------------------------------------------------------
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove uma tarefa (soft delete)",
)
def delete_task(
    task_id: int = Path(..., ge=1),
    service: TaskService = Depends(_get_service),
) -> Response:
    """Marca ``deleted_at``; nada é apagado de fato."""
    service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
