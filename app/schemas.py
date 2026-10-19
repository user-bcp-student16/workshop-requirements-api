from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel

DEFAULT_TASK_STATUS = "TODO"
DEFAULT_TASK_PRIORITY = "MEDIUM"


class AuthenticatedIdentity(BaseModel):
    username: str
    role: str


class TaskCreateRequest(RootModel[dict[str, Any]]):
    def string_value(self, field_name: str, default: str = "") -> str:
        return str(self.root.get(field_name, default))

    @property
    def title(self) -> str:
        return self.string_value("title")

    @property
    def description(self) -> str:
        return self.string_value("description")

    @property
    def status(self) -> str:
        return self.string_value("status", DEFAULT_TASK_STATUS)

    @property
    def priority(self) -> str:
        return self.string_value("priority", DEFAULT_TASK_PRIORITY)


class TaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(alias="createdAt")


class TaskSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner: str
    total: int
    by_status: dict[str, int] = Field(alias="byStatus")
    high_priority_open: int = Field(alias="highPriorityOpen")


class RequirementUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner: str
    file_name: str | None = Field(alias="fileName")
    stored_at: str = Field(alias="storedAt")
    size: int


class BackendHealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    requested_by: str = Field(alias="requestedBy")
    status: int
    body: str