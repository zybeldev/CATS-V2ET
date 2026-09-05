from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Protocol
from uuid import UUID

from cats.agents.tea.agent import ExecutionRuntimeState


class ExecutionStateStore(Protocol):
    def save(self, state: ExecutionRuntimeState) -> None:
        ...
    def load(self, execution_id: UUID) -> ExecutionRuntimeState | None:
        ...
    def list_active(self) -> list[ExecutionRuntimeState]:
        ...


class InMemoryExecutionStateStore:
    """Deterministic durable-state abstraction used by tests.

    A SQL-backed implementation can replace this without changing runtime
    recovery semantics.
    """

    def __init__(self):
        self._states: dict[UUID, ExecutionRuntimeState] = {}

    def save(self, state: ExecutionRuntimeState) -> None:
        self._states[state.execution_id] = deepcopy(state)

    def load(self, execution_id: UUID) -> ExecutionRuntimeState | None:
        state = self._states.get(execution_id)
        return None if state is None else deepcopy(state)

    def list_active(self) -> list[ExecutionRuntimeState]:
        return [
            deepcopy(s)
            for s in self._states.values()
            if s.status not in {"COMPLETED", "SUPERSEDED", "TERMINATED"}
        ]
