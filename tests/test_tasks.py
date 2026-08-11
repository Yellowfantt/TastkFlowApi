"""Testes do CRUD e fluxos da entidade Task.

Cobre os endpoints via TestClient:
    POST /tasks
    GET  /tasks
    GET  /tasks/{id}
    PATCH /tasks/{id}
    POST /tasks/{id}/complete
    DELETE /tasks/{id}
    GET  /tasks/stats
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.models.task import Task
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _create_payload(**overrides) -> dict:
    payload = {
        "title": "Estudar FastAPI",
        "description": "Ler a documentação oficial",
        "priority": "medium",
        "due_date": None,
    }
    payload.update(overrides)
    return payload


# ----------------------------------------------------------------------
# CREATE
# ----------------------------------------------------------------------
def test_create_task_returns_201_and_pending(client: TestClient) -> None:
    response = client.post("/tasks", json=_create_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] >= 1
    assert body["title"] == "Estudar FastAPI"
    assert body["status"] == "pending"
    assert body["priority"] == "medium"
    assert body["completed_at"] is None


def test_create_task_with_invalid_title_returns_422(client: TestClient) -> None:
    # Título vazio deve falhar a validação do Pydantic (min_length=1).
    response = client.post("/tasks", json=_create_payload(title=""))
    assert response.status_code == 422


def test_create_task_with_invalid_priority_returns_422(client: TestClient) -> None:
    response = client.post("/tasks", json=_create_payload(priority="urgent"))
    assert response.status_code == 422


# ----------------------------------------------------------------------
# LIST
# ----------------------------------------------------------------------
def test_list_tasks_starts_empty(client: TestClient) -> None:
    response = client.get("/tasks")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_tasks_returns_paginated_results(client: TestClient) -> None:
    for i in range(3):
        client.post("/tasks", json=_create_payload(title=f"Tarefa {i}"))

    response = client.get("/tasks?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_list_tasks_filters_by_status(client: TestClient) -> None:
    # Cria duas, completa uma.
    a = client.post("/tasks", json=_create_payload(title="A")).json()
    client.post("/tasks", json=_create_payload(title="B")).json()
    client.post(f"/tasks/{a['id']}/complete")

    response = client.get("/tasks?status=completed")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A"


def test_list_tasks_filters_by_search(client: TestClient) -> None:
    client.post("/tasks", json=_create_payload(title="Comprar pão"))
    client.post("/tasks", json=_create_payload(title="Estudar Python"))

    response = client.get("/tasks?search=python")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Estudar Python"


# ----------------------------------------------------------------------
# READ by id
# ----------------------------------------------------------------------
def test_get_task_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]


def test_get_task_returns_200(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload()).json()

    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


# ----------------------------------------------------------------------
# PATCH
# ----------------------------------------------------------------------
def test_patch_task_updates_only_provided_fields(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload(title="Original")).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": "Atualizado"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Atualizado"
    assert body["priority"] == "medium"  # preservado


def test_patch_task_valid_transition_pending_to_in_progress(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload()).json()

    response = client.patch(f"/tasks/{created['id']}", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_patch_task_rejects_invalid_transition_returns_409(
    client: TestClient, db_engine
) -> None:
    """Força um status desconhecido no banco via a MESMA engine em memória.

    Depois tenta a transição inválida via a API; espera 409 (regra de negócio).
    """
    created = client.post("/tasks", json=_create_payload()).json()

    TestingSessionLocal = sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        class_=Session,
        expire_on_commit=False,
    )
    with TestingSessionLocal() as session:
        session.execute(
            update(Task).where(Task.id == created["id"]).values(status="archived")
        )
        session.commit()

    response = client.patch(f"/tasks/{created['id']}", json={"status": "pending"})
    assert response.status_code == 409
    assert "archived" in response.json()["detail"]


def test_patch_task_rejects_unknown_status_value_with_422(client: TestClient) -> None:
    """Validação do enum no schema: status fora do conjunto retorna 422."""
    created = client.post("/tasks", json=_create_payload()).json()
    response = client.patch(f"/tasks/{created['id']}", json={"status": "archived"})
    assert response.status_code == 422


def test_patch_task_completed_fills_completed_at(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload()).json()
    assert created["completed_at"] is None

    response = client.patch(f"/tasks/{created['id']}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["completed_at"] is not None


# ----------------------------------------------------------------------
# COMPLETE
# ----------------------------------------------------------------------
def test_complete_task_is_idempotent(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload()).json()

    first = client.post(f"/tasks/{created['id']}/complete")
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    second = client.post(f"/tasks/{created['id']}/complete")
    assert second.status_code == 200
    assert second.json()["status"] == "completed"


def test_complete_nonexistent_task_returns_404(client: TestClient) -> None:
    response = client.post("/tasks/999/complete")
    assert response.status_code == 404


# ----------------------------------------------------------------------
# DELETE
# ----------------------------------------------------------------------
def test_delete_task_soft_deletes(client: TestClient) -> None:
    created = client.post("/tasks", json=_create_payload()).json()

    response = client.delete(f"/tasks/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # Após o delete, GET deve retornar 404.
    get_response = client.get(f"/tasks/{created['id']}")
    assert get_response.status_code == 404

    # E o item não deve aparecer na listagem.
    list_response = client.get("/tasks")
    assert list_response.json()["total"] == 0


def test_delete_nonexistent_task_returns_404(client: TestClient) -> None:
    response = client.delete("/tasks/999")
    assert response.status_code == 404


# ----------------------------------------------------------------------
# STATS
# ----------------------------------------------------------------------
def test_stats_counts_correctly(client: TestClient) -> None:
    # 2 pending, 1 in_progress, 1 completed.
    a = client.post("/tasks", json=_create_payload(title="A")).json()
    client.post("/tasks", json=_create_payload(title="B")).json()
    c = client.post("/tasks", json=_create_payload(title="C")).json()
    client.post("/tasks", json=_create_payload(title="D")).json()

    client.patch(f"/tasks/{a['id']}", json={"status": "in_progress"})
    client.patch(f"/tasks/{c['id']}", json={"status": "completed"})

    response = client.get("/tasks/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["pending"] == 2
    assert body["in_progress"] == 1
    assert body["completed"] == 1


def test_stats_counts_overdue(client: TestClient) -> None:
    # Tarefa atrasada (due_date no passado, status pending).
    past = (datetime.now(tz=UTC) - timedelta(days=2)).isoformat()
    client.post("/tasks", json=_create_payload(title="Atrasada", due_date=past))

    # Tarefa futura — não conta como atrasada.
    future = (datetime.now(tz=UTC) + timedelta(days=2)).isoformat()
    client.post("/tasks", json=_create_payload(title="Futura", due_date=future))

    # Tarefa atrasada mas já concluída — não conta.
    overdue_done = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    done = client.post(
        "/tasks", json=_create_payload(title="Atrasada concluída", due_date=overdue_done)
    ).json()
    client.patch(f"/tasks/{done['id']}", json={"status": "completed"})

    response = client.get("/tasks/stats")
    assert response.status_code == 200
    assert response.json()["overdue"] == 1
