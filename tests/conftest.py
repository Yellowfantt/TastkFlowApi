"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.core.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_engine():
    """Engine SQLite em memória, compartilhada entre conexões da mesma thread.

    ``StaticPool`` mantém a mesma conexão viva para que múltiplas ``Session``
    vejam o mesmo banco (sem isso, o SQLite em memória criaria um banco
    novo por conexão e os testes falhariam).
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    # Limpa as tabelas para o próximo teste (cria engine novo no próximo uso).
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine) -> Generator[Session, None, None]:
    """Sessão de teste ligada ao engine em memória."""
    TestingSessionLocal = sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        class_=Session,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine) -> Generator[TestClient, None, None]:
    """Cliente HTTP de teste com DB SQLite em memória injetado.

    Sobrescrevemos ``get_db`` para que cada request use a mesma engine
    em memória (StaticPool) onde as tabelas já foram criadas.
    """
    TestingSessionLocal = sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        class_=Session,
        expire_on_commit=False,
    )

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
