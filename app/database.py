import sqlite3
from pathlib import Path

CREATE_TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""
INSERT_INITIAL_TASKS_SQL = """
INSERT INTO tasks(title, description, status, owner, priority, created_at)
VALUES (?, ?, ?, ?, ?, datetime('now'))
"""
INITIAL_TASKS = (
    ("Refactor login", "Separar responsabilidades en frontend", "TODO", "student", "HIGH"),
    ("Review API", "Revisar seguridad de endpoints", "IN_PROGRESS", "student", "MEDIUM"),
    ("Trainer notes", "Preparar retrospectiva", "TODO", "trainer", "LOW"),
)


def create_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(CREATE_TASKS_TABLE_SQL)
    task_count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if task_count == 0:
        connection.executemany(INSERT_INITIAL_TASKS_SQL, INITIAL_TASKS)
        connection.commit()