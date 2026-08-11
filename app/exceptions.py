"""Exceções de domínio e handlers globais.

As exceções daqui NÃO conhecem HTTP — são problemas de regra de negócio.
Os routers/services lançam-nas e o handler global (em ``main.py``) traduz
para ``HTTPException`` com o status code apropriado.

Por que não lançar ``HTTPException`` direto no Service?
    Porque o Service não deve conhecer HTTP. Isso quebra testes de
    Service (que rodariam sem FastAPI) e amarra a camada a um framework.
"""

from __future__ import annotations


class TaskFlowError(Exception):
    """Exceção base — todas as outras herdam desta."""


class TaskNotFoundError(TaskFlowError):
    """A tarefa não existe ou foi removida (soft delete)."""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"Tarefa com id={task_id} não encontrada.")
        self.task_id = task_id


class InvalidStatusTransitionError(TaskFlowError):
    """Transição de status não permitida pela regra de negócio."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Transição de status não permitida: {current!r} -> {target!r}."
        )
        self.current = current
        self.target = target
