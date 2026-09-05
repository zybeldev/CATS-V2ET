from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .base import MaterialContract


class Assessment(MaterialContract):
    assessment_id: UUID
    financial_instrument_id: UUID
    assessment_type: Literal[
        "STRATEGIC",
        "TACTICAL",
        "CANDIDATE",
        "HOLDING",
        "MATERIAL_EVENT",
        "PORTFOLIO_RELEVANT_INTELLIGENCE",
    ]
    horizon: Literal["STRATEGIC", "TACTICAL"]
    summary: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    valid_until: datetime | None = None
    evidence_item_ids: list[UUID] = Field(default_factory=list)
    tss_measurement_set_ids: list[UUID] = Field(default_factory=list)
