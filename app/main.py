"""Ponto de entrada da API FastAPI.

Aqui ficam:
    * Instanciação da ``FastAPI`` com metadados (título, descrição, versão).
    * ``lifespan`` — código que roda no startup/shutdown (criar tabelas).
    * Registro dos routers.
    * Handlers globais de exceção (traduzem erros de domínio -> HTTPException).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.database import engine  # noqa: F401  (mantido para uso futuro)
from app.exceptions import InvalidStatusTransitionError, TaskFlowError, TaskNotFoundError
from app.routers import health_router, tasks_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Lifespan mínimo.

    O schema do banco é controlado por migrations Alembic
    (``alembic upgrade head``), NÃO por ``create_all`` aqui. Manter este
    hook vazio em runtime evita criar tabelas duas vezes (uma no startup
    e outra via migrations) — o que pode mascarar drift de schema.
    """
    yield
    # No shutdown não há nada a fazer — o engine fecha com o processo.


app = FastAPI(
    title="TaskFlow API",
    description="API de gerenciamento de tarefas construída com FastAPI + SQLAlchemy + SQLite.",
    version="0.1.0",
    lifespan=lifespan,
)

# Rotas
app.include_router(health_router)
app.include_router(tasks_router)


# ----------------------------------------------------------------------
# Handlers globais
# ----------------------------------------------------------------------
# Cada exceção de domínio vira um HTTPException com o status code certo.
# Manter isso centralizado evita espalhar ``raise HTTPException(...)``
# nos services e routers.
@app.exception_handler(TaskNotFoundError)
def _task_not_found_handler(_: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidStatusTransitionError)
def _invalid_transition_handler(_: Request, exc: InvalidStatusTransitionError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(TaskFlowError)
def _generic_domain_handler(_: Request, exc: TaskFlowError) -> JSONResponse:
    """Fallback para qualquer outra exceção de domínio não mapeada."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )
