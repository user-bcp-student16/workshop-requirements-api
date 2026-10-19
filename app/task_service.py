import sqlite3
from collections import Counter
from typing import Any

from app import task_repository

DEFAULT_TASK_STATUS = "TODO"
DEFAULT_TASK_PRIORITY = "MEDIUM"
HIGH_PRIORITY = "HIGH"
CLOSED_TASK_STATUSES = {"DONE", "ARCHIVED"}


def _as_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "owner": row["owner"],
        "priority": row["priority"],
        "createdAt": row["created_at"],
    }


def list_tasks(
    connection: sqlite3.Connection,
    identity: dict[str, str],
) -> list[dict[str, Any]]:
    rows = task_repository.list_tasks_by_owner(connection, identity["username"])
    return [_as_task(row) for row in rows]


def create_task(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any]:
    row = task_repository.insert_task(
        connection,
        title=str(payload.get("title", "")),
        description=str(payload.get("description", "")),
        status=str(payload.get("status", DEFAULT_TASK_STATUS)),
        owner=identity["username"],
        priority=str(payload.get("priority", DEFAULT_TASK_PRIORITY)),
    )
    return _as_task(row)


def summarize_tasks(
    connection: sqlite3.Connection,
    identity: dict[str, str],
) -> dict[str, Any]:
    owner = identity["username"]
    rows = task_repository.get_summary_tasks(connection, owner)
    status_counts = Counter(row["status"] for row in rows)
    high_priority_open = sum(
        row["priority"] == HIGH_PRIORITY and row["status"] not in CLOSED_TASK_STATUSES
        for row in rows
    )
    return {
        "owner": owner,
        "total": len(rows),
        "byStatus": dict(status_counts),
        "highPriorityOpen": high_priority_open,
    }