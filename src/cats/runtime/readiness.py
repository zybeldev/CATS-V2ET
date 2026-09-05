from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    detail: str


class ReadinessService:
    def __init__(self):
        self.checks: list[ReadinessCheck] = []

    def run_check(self, name: str, fn: Callable[[], str]) -> ReadinessCheck:
        try:
            detail = fn()
            check = ReadinessCheck(name=name, passed=True, detail=detail)
        except Exception as exc:
            check = ReadinessCheck(
                name=name,
                passed=False,
                detail=f"{type(exc).__name__}: {exc}",
            )
        self.checks.append(check)
        return check

    @property
    def ready(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)
