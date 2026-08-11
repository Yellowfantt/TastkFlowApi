"""Infraestrutura de banco de dados (SQLAlchemy).

Este módulo é responsável por:
    * Criar o ``engine`` (lazy — não conecta até alguém pedir uma conexão).
    * Expor a ``SessionLocal`` (fábrica de sessões).
    * Declarar a ``Base`` que os ``models`` herdarão.
    * Fornecer ``get_db()`` como dependência do FastAPI.

A criação das tabelas (``Base.metadata.create_all()``) NÃO acontece aqui —
fica a cargo de quem sobe a aplicação (será o ``lifespan`` em ``main.py``).
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------
# ``create_engine`` SEMPRE é lazy:
#   * Não abre conexão TCP/arquivo até alguém chamar ``engine.connect()``,
#     uma ``Session`` abrir uma transação, ou ``Base.metadata.create_all()``.
#   * Aqui só configuramos o pool e os connect_args.
#
# Por que ``check_same_thread=False``?
#   O SQLite, por padrão, só permite que a thread que criou a conexão
#   a utilize. O FastAPI pode executar diferentes requests em threads
#   distintas, então precisamos liberar essa checagem.
#
# Por que NÃO ``pool_pre_ping``?
#   O ``pool_pre_ping`` testa conexões ociosas — desnecessário para SQLite
#   (banco embutido, sem rede). Mantemos o motor enxuto.
# ----------------------------------------------------------------------
_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


# ----------------------------------------------------------------------
# Session factory
# ----------------------------------------------------------------------
# ``autoflush=False`` e ``autocommit=False`` dão controle explícito via
# ``session.commit()`` no serviço. É o padrão recomendado para uso com
# FastAPI (transações por request).
# ----------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
    expire_on_commit=False,
)


# ----------------------------------------------------------------------
# Declarative Base
# ----------------------------------------------------------------------
# Todos os ``models`` herdarão desta classe para que o SQLAlchemy possa
# registrar suas tabelas e permitir ``Base.metadata.create_all()``.
# ----------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base declarativa para todos os models ORM."""


# ----------------------------------------------------------------------
# Dependência FastAPI
# ----------------------------------------------------------------------
# Injetamos via ``Depends(get_db)`` nas rotas. A sessão é fechada
# mesmo se a request levantar exceção (garantido pelo ``finally``).
# ----------------------------------------------------------------------
def get_db() -> Generator[Session, Any, None]:
    """Fornece uma ``Session`` por request e garante o fechamento."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
