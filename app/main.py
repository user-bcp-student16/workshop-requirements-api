from __future__ import annotations

import os
from pathlib import Path

from fastapi import Body, Depends, FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import task_service
from app.backend_health_service import get_backend_health
from app.database import create_connection, initialize_database
from app.requirement_service import store_requirement
from app.schemas import (
    AuthenticatedIdentity,
    BackendHealthResponse,
    RequirementUploadResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskSummaryResponse,
)
from app.security import legacy_identity

DEFAULT_DB_PATH = "./data/workshop.db"
DEFAULT_UPLOAD_DIR = "./uploads"


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", DEFAULT_DB_PATH)
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = create_connection(selected_db)
    initialize_database(connection)

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/tasks", response_model=list[TaskResponse])
    def list_tasks(
        owner: str | None = Query(default=None),
        identity: AuthenticatedIdentity = Depends(legacy_identity),
    ) -> list[TaskResponse]:
        return task_service.list_tasks(connection, identity)

    @app.post("/api/tasks", status_code=201, response_model=TaskResponse)
    def create_task(
        payload: TaskCreateRequest = Body(...),
        identity: AuthenticatedIdentity = Depends(legacy_identity),
    ) -> TaskResponse:
        return task_service.create_task(connection, payload, identity)

    @app.get("/api/summary", response_model=TaskSummaryResponse)
    def summary(
        owner: str | None = Query(default=None),
        identity: AuthenticatedIdentity = Depends(legacy_identity),
    ) -> TaskSummaryResponse:
        return task_service.summarize_tasks(connection, identity)

    @app.post("/api/requirements", status_code=201, response_model=RequirementUploadResponse)
    async def upload_requirement(
        file: UploadFile = File(...),
        identity: AuthenticatedIdentity = Depends(legacy_identity),
    ) -> RequirementUploadResponse:
        return await store_requirement(file, selected_uploads, identity.username)

    @app.get("/api/backend-health", response_model=BackendHealthResponse)
    def backend_health(
        identity: AuthenticatedIdentity = Depends(legacy_identity),
    ) -> BackendHealthResponse:
        return get_backend_health(identity.username)

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
