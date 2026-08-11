"""Schemas Pydantic compartilhados entre endpoints."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Formato padrão de resposta de erro."""

    detail: str = Field(..., description="Mensagem de erro legível para o cliente.")


class PaginationParams(BaseModel):
    """Parâmetros de paginação aceitos via query string."""

    page: int = Field(default=1, ge=1, description="Número da página (1-based).")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Quantidade de itens por página (1-100)."
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope genérico para listas paginadas."""

    items: list[T] = Field(..., description="Itens da página atual.")
    total: int = Field(..., ge=0, description="Total de itens (considerando filtros).")
    page: int = Field(..., ge=1, description="Página atual.")
    page_size: int = Field(..., ge=1, description="Tamanho da página.")

    model_config = ConfigDict(arbitrary_types_allowed=True)
