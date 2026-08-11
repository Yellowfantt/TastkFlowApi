"""Schemas Pydantic (DTOs) da aplicação."""

from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.task import (
    TaskBase,
    TaskCreate,
    TaskFilters,
    TaskRead,
    TaskStats,
    TaskUpdate,
)

__all__ = [
    "ErrorResponse",
    "PaginatedResponse",
    "TaskBase",
    "TaskCreate",
    "TaskFilters",
    "TaskRead",
    "TaskStats",
    "TaskUpdate",
]
