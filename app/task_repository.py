import sqlite3

TASK_COLUMNS = "id, title, description, status, owner, priority, created_at"


def list_tasks_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner = ? ORDER BY id",
        (owner,),
    ).fetchall()


def insert_task(
    connection: sqlite3.Connection,
    title: str,
    description: str,
    status: str,
    owner: str,
    priority: str,
) -> sqlite3.Row:
    cursor = connection.execute(
        """
        INSERT INTO tasks(title, description, status, owner, priority, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (title, description, status, owner, priority),
    )
    connection.commit()
    row = connection.execute(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Inserted task could not be retrieved")
    return row


def get_summary_tasks(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT status, priority FROM tasks WHERE owner = ?",
        (owner,),
    ).fetchall()