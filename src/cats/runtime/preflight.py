from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PreflightResult:
    name: str
    passed: bool
    detail: str


class PreflightRunner:
    """Runs fail-closed dependency checks without creating financial intent."""

    def __init__(self):
        self.results: list[PreflightResult] = []

    def check(self, name: str, fn: Callable[[], str]) -> PreflightResult:
        try:
            detail = fn()
            result = PreflightResult(name, True, detail)
        except Exception as exc:
            result = PreflightResult(name, False, f"{type(exc).__name__}: {exc}")
        self.results.append(result)
        return result

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    def require_pass(self) -> None:
        if not self.passed:
            failed = ", ".join(r.name for r in self.results if not r.passed)
            raise RuntimeError(f"Preflight failed: {failed}")
