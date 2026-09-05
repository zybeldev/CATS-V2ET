from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .base import MaterialContract


class ValidationRuleResult(BaseModel):
    rule_code: str
    rule_version: str
    result: Literal["PASS", "FAIL"]
    configured_value: str | None = None
    observed_value: str | None = None
    reason: str | None = None


class ValidationResult(MaterialContract):
    validation_result_id: UUID
    portfolio_decision_id: UUID
    result: Literal["PASS", "FAIL"]
    rule_results: list[ValidationRuleResult] = Field(default_factory=list)
