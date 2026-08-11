"""Serviço de regras de negócio para a entidade Task.

Concentra validações, transições de estado e cálculos. Conhece apenas
Repository e Models — NEM HTTP, NEM Pydantic de saída.

Erros são expressos via exceções de domínio (ver ``app/exceptions.py``).
O router as traduz para HTTPException via handlers globais.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.exceptions import InvalidStatusTransitionError, TaskNotFoundError
from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskFilters, TaskStats, TaskUpdate

# Transições permitidas pela máquina de estados.
#
# pending    -> in_progress | completed
# in_progress -> completed | pending (reabrir)
# completed  -> in_progress (reabrir) | pending
#
# Decisão: não bloqueamos re-abrir tarefas concluídas — útil quando o
# usuário marcou por engano. ``completed_at`` será resetado.
VALID_TRANSITIONS: dict[str, set[str]] = {
    TaskStatus.PENDING.value: {
        TaskStatus.IN_PROGRESS.value,
        TaskStatus.COMPLETED.value,
    },
    TaskStatus.IN_PROGRESS.value: {
        TaskStatus.PENDING.value,
        TaskStatus.COMPLETED.value,
    },
    TaskStatus.COMPLETED.value: {
        TaskStatus.PENDING.value,
        TaskStatus.IN_PROGRESS.value,
    },
}


class TaskService:
    """Orquestra operações de tarefa aplicando regras de negócio."""

    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create_task(self, data: TaskCreate) -> Task:
        """Cria uma tarefa sempre em status=pending.

        O título já vem validado pelo Pydantic; aqui só normalizamos a
        criação (campo ``status`` é forçado, ignorando o que vier).
        """
        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority.value,
            status=TaskStatus.PENDING.value,
            due_date=data.due_date,
        )
        return self._repo.create(task)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_task(self, task_id: int) -> Task:
        """Busca por id, levantando ``TaskNotFoundError`` se não existir."""
        task = self._repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def list_tasks(self, filters: TaskFilters) -> tuple[Sequence[Task], int]:
        """Delega ao repository, sem transformação."""
        return self._repo.list(
            status=filters.status,
            priority=filters.priority,
            search=filters.search,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Update (parcial)
    # ------------------------------------------------------------------
    def update_task(self, task_id: int, data: TaskUpdate) -> Task:
        """Atualiza apenas os campos fornecidos, validando transições."""
        task = self.get_task(task_id)

        # ``exclude_unset`` garante que campos não enviados pelo cliente
        # não sobrescrevam valores existentes.
        updates = data.model_dump(exclude_unset=True)

        # Validação de transição de status (se enviada).
        if "status" in updates:
            self._validate_status_transition(
                current=task.status,
                target=updates["status"],
            )
            # Converte enum -> seu .value para persistir string.
            new_status = updates["status"]
            updates["status"] = new_status.value if isinstance(new_status, TaskStatus) else new_status

            # Regra de negócio: ``completed_at`` espelha o status.
            if updates["status"] == TaskStatus.COMPLETED.value:
                updates["completed_at"] = datetime.now(tz=UTC)
            else:
                # Reabrir tarefa: limpamos a data de conclusão.
                updates["completed_at"] = None

        # Normaliza enums -> values quando aplicável.
        if "priority" in updates:
            priority = updates["priority"]
            if isinstance(priority, TaskPriority):
                updates["priority"] = priority.value

        return self._repo.update(task, fields=updates)

    # ------------------------------------------------------------------
    # Complete (atalho semântico)
    # ------------------------------------------------------------------
    def complete_task(self, task_id: int) -> Task:
        """Marca a tarefa como concluída, se ainda não estiver."""
        task = self.get_task(task_id)
        if task.status == TaskStatus.COMPLETED.value:
            # Idempotente: chamar /complete em uma tarefa já concluída não falha.
            return task

        self._validate_status_transition(
            current=task.status,
            target=TaskStatus.COMPLETED.value,
        )
        return self._repo.update(
            task,
            fields={
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.now(tz=UTC),
            },
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_task(self, task_id: int) -> None:
        """Soft delete: marca ``deleted_at``."""
        task = self.get_task(task_id)
        self._repo.soft_delete(task)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> TaskStats:
        """Calcula agregações."""
        counts = self._repo.count_by_status()
        overdue = self._repo.count_overdue()
        total = sum(counts.values())
        return TaskStats(
            total=total,
            pending=counts[TaskStatus.PENDING.value],
            in_progress=counts[TaskStatus.IN_PROGRESS.value],
            completed=counts[TaskStatus.COMPLETED.value],
            overdue=overdue,
        )

    # ------------------------------------------------------------------
    # Regras internas
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_status_transition(current: str, target: str) -> None:
        """Lança ``InvalidStatusTransitionError`` se a transição não é válida."""
        if current == target:
            return  # sem transição real
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStatusTransitionError(current=current, target=target)
