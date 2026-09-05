from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .environment_doctor import inspect_environment


@dataclass(frozen=True)
class RealRunGate:
    ready: bool
    failed_checks: tuple[str, ...]


def evaluate_real_run_gate(
    env: dict[str, str] | None = None,
    *,
    require_openai: bool = True,
) -> RealRunGate:
    checks = inspect_environment(env, require_openai=require_openai)
    failed = tuple(c.name for c in checks if not c.passed)
    return RealRunGate(ready=not failed, failed_checks=failed)


def require_real_run_ready(
    env: dict[str, str] | None = None,
    *,
    require_openai: bool = True,
) -> None:
    gate = evaluate_real_run_gate(env, require_openai=require_openai)
    if not gate.ready:
        raise RuntimeError(
            "Real PAPER run blocked. Failed checks: " + ", ".join(gate.failed_checks)
        )
