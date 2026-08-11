"""Repositório da entidade Task.

Única camada que importa SQLAlchemy e conhece a tabela ``tasks``.
Operações CRUD puras + queries filtradas. SEM regras de negócio.

Todas as queries de leitura filtram ``deleted_at IS NULL`` — soft delete
deve ser transparente para o resto da aplicação.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus


class TaskRepository:
    """Operações de persistência para ``Task``.

    Esta classe é stateful apenas no sentido de manter a ``Session``.
    Pode ser instanciada por request (via ``Depends``) — não mantém
    estado entre requests.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, task: Task) -> Task:
        """Persiste uma nova tarefa e retorna o objeto com ``id``."""
        self._db.add(task)
        self._db.commit()
        self._db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_by_id(self, task_id: int) -> Task | None:
        """Busca por id, ignorando soft-deleted."""
        stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        return self._db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Task], int]:
        """Lista tarefas com filtros opcionais, paginadas.

        Retorna ``(itens_da_página, total_geral)``.
        """
        stmt = select(Task).where(Task.deleted_at.is_(None))

        if status is not None:
            stmt = stmt.where(Task.status == status.value)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority.value)
        if search:
            # LIKE case-insensitive — ``func.lower`` evita problemas de collation.
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Task.title).like(pattern),
                    func.lower(Task.description).like(pattern),
                )
            )

        # Total antes da paginação (para o front saber quantas páginas existem).
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self._db.execute(count_stmt).scalar_one()

        # Ordenação estável: mais recentes primeiro.
        stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = self._db.execute(stmt).scalars().all()
        return items, total

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, task: Task, *, fields: dict[str, object]) -> Task:
        """Atualiza apenas os campos fornecidos e persiste."""
        for key, value in fields.items():
            setattr(task, key, value)
        self._db.commit()
        self._db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def soft_delete(self, task: Task) -> None:
        """Marca ``deleted_at`` com a hora atual."""
        task.deleted_at = datetime.now(tz=UTC)
        self._db.commit()
        self._db.refresh(task)

    # ------------------------------------------------------------------
    # Aggregations (para /stats)
    # ------------------------------------------------------------------
    def count_by_status(self) -> dict[str, int]:
        """Conta tarefas ativas agrupadas por status."""
        stmt = (
            select(Task.status, func.count(Task.id))
            .where(Task.deleted_at.is_(None))
            .group_by(Task.status)
        )
        rows = self._db.execute(stmt).all()
        # Garante chaves para todos os status, mesmo que zero.
        result: dict[str, int] = {
            TaskStatus.PENDING.value: 0,
            TaskStatus.IN_PROGRESS.value: 0,
            TaskStatus.COMPLETED.value: 0,
        }
        for status_value, count in rows:
            result[status_value] = count
        return result

    def count_overdue(self, *, now: datetime | None = None) -> int:
        """Conta tarefas ativas, não concluídas e com due_date no passado."""
        moment = now or datetime.now(tz=UTC)
        stmt = (
            select(func.count(Task.id))
            .where(
                Task.deleted_at.is_(None),
                Task.status != TaskStatus.COMPLETED.value,
                Task.due_date.is_not(None),
                Task.due_date < moment,
            )
        )
        return int(self._db.execute(stmt).scalar_one())
