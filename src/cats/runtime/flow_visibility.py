from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _label(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _format_scalar(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


@dataclass(frozen=True)
class FlowVisibilityStage:
    name: str
    status: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": _json_safe(self.details),
        }


@dataclass(frozen=True)
class FlowVisibilityReport:
    """Structured operator/UI view of one CATS vertical slice.

    This is an observability/read-model object only. It does not participate in
    authority, validation, optimization, or execution decisions.
    """

    flow_id: UUID
    symbol: str
    outcome: str
    stages: tuple[FlowVisibilityStage, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "flow_id": str(self.flow_id),
            "symbol": self.symbol,
            "outcome": self.outcome,
            "stages": [stage.as_dict() for stage in self.stages],
        }

    def render_text(self) -> str:
        lines = [
            f"CATS FLOW — {self.symbol}",
            "=" * 78,
            f"Flow ID: {self.flow_id}",
            f"Outcome: {self.outcome}",
            "",
        ]
        for index, stage in enumerate(self.stages, start=1):
            lines.append(f"{index}. {stage.name} [{stage.status}]")
            self._render_mapping(lines, stage.details, indent="   ")
            lines.append("")
        return "\n".join(lines).rstrip()

    @classmethod
    def _render_mapping(cls, lines: list[str], mapping: dict[str, Any], *, indent: str) -> None:
        for key, value in mapping.items():
            label = _label(str(key))
            if isinstance(value, dict):
                lines.append(f"{indent}{label}:")
                cls._render_mapping(lines, value, indent=indent + "  ")
            elif isinstance(value, (list, tuple)):
                lines.append(f"{indent}{label}:")
                if not value:
                    lines.append(f"{indent}  (none)")
                    continue
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{indent}  -")
                        cls._render_mapping(lines, item, indent=indent + "    ")
                    else:
                        lines.append(f"{indent}  - {_format_scalar(item)}")
            else:
                lines.append(f"{indent}{label}: {_format_scalar(value)}")


class FlowVisibilityBuilder:
    """Mutable builder kept inside runtime while a flow is progressing."""

    def __init__(self, *, flow_id: UUID, symbol: str) -> None:
        self.flow_id = flow_id
        self.symbol = symbol
        self._stages: list[FlowVisibilityStage] = []

    def stage(self, name: str, *, status: str = "READY", **details: Any) -> None:
        stage = FlowVisibilityStage(name=name, status=status, details=details)
        for index, existing in enumerate(self._stages):
            if existing.name == name:
                self._stages[index] = stage
                return
        self._stages.append(stage)

    def build(self, *, outcome: str) -> FlowVisibilityReport:
        return FlowVisibilityReport(
            flow_id=self.flow_id,
            symbol=self.symbol,
            outcome=outcome,
            stages=tuple(self._stages),
        )
