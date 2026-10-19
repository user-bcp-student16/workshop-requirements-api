import sqlite3
from collections import Counter

from app import task_repository
from app.schemas import AuthenticatedIdentity, TaskCreateRequest, TaskResponse, TaskSummaryResponse

HIGH_PRIORITY = "HIGH"
CLOSED_TASK_STATUSES = {"DONE", "ARCHIVED"}


def _as_task(row: sqlite3.Row) -> TaskResponse:
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        owner=row["owner"],
        priority=row["priority"],
        createdAt=row["created_at"],
    )


def list_tasks(
    connection: sqlite3.Connection,
    identity: AuthenticatedIdentity,
) -> list[TaskResponse]:
    rows = task_repository.list_tasks_by_owner(connection, identity.username)
    return [_as_task(row) for row in rows]


def create_task(
    connection: sqlite3.Connection,
    payload: TaskCreateRequest,
    identity: AuthenticatedIdentity,
) -> TaskResponse:
    row = task_repository.insert_task(
        connection,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        owner=identity.username,
        priority=payload.priority,
    )
    return _as_task(row)


def summarize_tasks(
    connection: sqlite3.Connection,
    identity: AuthenticatedIdentity,
) -> TaskSummaryResponse:
    owner = identity.username
    rows = task_repository.get_summary_tasks(connection, owner)
    status_counts = Counter(row["status"] for row in rows)
    high_priority_open = sum(
        row["priority"] == HIGH_PRIORITY and row["status"] not in CLOSED_TASK_STATUSES
        for row in rows
    )
    return TaskSummaryResponse(
        owner=owner,
        total=len(rows),
        byStatus=dict(status_counts),
        highPriorityOpen=high_priority_open,
    )