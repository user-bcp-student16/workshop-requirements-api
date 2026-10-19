import base64
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import urllib3
from fastapi.testclient import TestClient

from app import main, task_repository
from app.main import create_app


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert set(tasks[0]) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert set(created.json()) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }
    assert created.json()["owner"] == "student"
    assert summary.status_code == 200
    assert set(summary.json()) == {"owner", "total", "byStatus", "highPriorityOpen"}
    assert summary.json()["total"] == 3


def test_task_listing_uses_authenticated_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=trainer", headers=headers("student"))

    assert response.status_code == 200
    assert [task["owner"] for task in response.json()] == ["student", "student"]


def test_task_listing_accepts_empty_owner_query(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_summary_uses_authenticated_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary?owner=trainer", headers=headers("student"))

    assert response.status_code == 200
    assert response.json()["owner"] == "student"
    assert response.json()["total"] == 2


def test_summary_for_owner_without_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks WHERE owner = ?", ("student",))
    app.state.connection.commit()

    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_task_creation_uses_authenticated_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers("student"),
            json={"title": "Owned by another user", "owner": "trainer"},
        )

    assert response.status_code == 201
    assert response.json()["owner"] == "student"


def test_task_creation_with_empty_payload_uses_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_task_creation_stringifies_values_and_ignores_extra_fields(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": 7,
                "description": None,
                "status": False,
                "priority": ["HIGH"],
                "owner": "trainer",
                "extra": "ignored",
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "7"
    assert response.json()["description"] == "None"
    assert response.json()["status"] == "False"
    assert response.json()["priority"] == "['HIGH']"
    assert response.json()["owner"] == "student"
    assert "extra" not in response.json()


def test_task_creation_rejects_non_object_json(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json=[])

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "dict_type"


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert set(response.json()) == {"owner", "fileName", "storedAt", "size"}
    assert response.json()["owner"] == "student"
    assert response.json()["size"] == len(b"Login must be accessible")
    assert (upload_dir / "requirements.txt").exists()


def test_uploads_empty_file_without_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirement", b"", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json()["fileName"] == "requirement"
    assert response.json()["size"] == 0
    assert (upload_dir / "requirement").read_bytes() == b""


def test_upload_rejects_missing_file(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("GET", "/api/tasks", {}),
        ("POST", "/api/tasks", {"json": {}}),
        ("GET", "/api/summary", {}),
        (
            "POST",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"text", "text/plain")}},
        ),
        ("GET", "/api/backend-health", {}),
    ],
)
def test_all_endpoints_reject_missing_authentication(
    tmp_path: Path,
    method: str,
    path: str,
    request_kwargs: dict[str, object],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.request(method, path, **request_kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_task_listing_database_error_returns_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_listing(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(task_repository, "list_tasks_by_owner", fail_listing)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 500


def test_task_creation_database_error_returns_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_insert(
        connection: sqlite3.Connection,
        title: str,
        description: str,
        status: str,
        owner: str,
        priority: str,
    ) -> sqlite3.Row:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(task_repository, "insert_task", fail_insert)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 500


def test_summary_database_error_returns_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_summary(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(task_repository, "get_summary_tasks", fail_summary)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/summary", headers=headers())

    assert response.status_code == 500


def test_upload_write_error_returns_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_write(path: Path, content: bytes) -> int:
        raise OSError("storage unavailable")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"text", "text/plain")},
        )

    assert response.status_code == 500


def test_backend_health_returns_backend_status_and_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTH_HEALTH_URL", raising=False)
    response_from_backend = SimpleNamespace(status=200, data=b"OK")
    monkeypatch.setattr(
        urllib3,
        "PoolManager",
        lambda: SimpleNamespace(
            request=lambda method, url, timeout: response_from_backend
        ),
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": "OK"}


def test_backend_health_preserves_non_success_backend_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response_from_backend = SimpleNamespace(status=503, data=b"unavailable")
    monkeypatch.setattr(
        urllib3,
        "PoolManager",
        lambda: SimpleNamespace(
            request=lambda method, url, timeout: response_from_backend
        ),
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 503,
        "body": "unavailable",
    }


def test_backend_health_reports_backend_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(method: str, url: str, timeout: float) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(
        urllib3,
        "PoolManager",
        lambda: SimpleNamespace(request=fail_request),
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "Backend health request failed",
    }


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_app_reuses_existing_database_without_reseeding(tmp_path: Path) -> None:
    db_path = str(tmp_path / "workshop.db")
    upload_dir = str(tmp_path / "uploads")
    first_app = create_app(db_path, upload_dir)
    first_app.state.connection.close()

    second_app = create_app(db_path, upload_dir)
    with TestClient(second_app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
