"""Model SQLAlchemy da entidade Task.

Define a tabela ``tasks`` e os enums de domínio (``TaskStatus`` e
``TaskPriority``). Apenas mapeamento objeto-relacional — sem regras
de negócio aqui.

Por que soft delete (``deleted_at``)?
    Preserva histórico e evita perda de dados quando uma tarefa é
    "removida". Consultas sempre filtram ``deleted_at IS NULL``.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskStatus(str, enum.Enum):
    """Estados possíveis de uma tarefa."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, enum.Enum):
    """Níveis de prioridade de uma tarefa."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    """Tabela ``tasks``.

    Mantemos colunas explícitas e tipos claros para garantir previsibilidade
    no SQLite e portabilidade para outros bancos no futuro.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Armazenamos o valor do enum (string) para legibilidade no banco e
    # portabilidade (SQLite não tem ENUM nativo; outros bancos aceitam).
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.PENDING.value,
        server_default=TaskStatus.PENDING.value,
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=TaskPriority.MEDIUM.value,
        server_default=TaskPriority.MEDIUM.value,
    )

    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Soft delete — preenchido quando a tarefa é "removida".
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # Acelera filtros comuns (listar por status, excluir soft-deleted).
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
