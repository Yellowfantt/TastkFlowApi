"""Endpoints de saúde da API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Verifica se a API e o banco estão respondendo")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Ping da API + SELECT 1 no banco.

    Se esta rota responder com ``status:"ok"``, a API está saudável
    e o banco está acessível.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
