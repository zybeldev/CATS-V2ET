from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MaterialContract(BaseModel):
    contract_id: UUID = Field(default_factory=uuid4)
    flow_id: UUID
    source: str
    destination: str
    created_at: datetime = Field(default_factory=utc_now)
    status: str = "CREATED"
    parent_ids: list[UUID] = Field(default_factory=list)
    configuration_version_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
