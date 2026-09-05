from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cats.agents.tea.agent import TradingExecutionAgent, ExecutionRuntimeState


class ExecutionStateStore(Protocol):
    def save(self, state: ExecutionRuntimeState) -> None:
        ...
    def load(self, execution_id: UUID) -> ExecutionRuntimeState | None:
        ...


class PersistentTradingExecutionAgent:
    """Persistence wrapper around TEA runtime transitions."""

    def __init__(self, tea: TradingExecutionAgent, state_store: ExecutionStateStore):
        self.tea = tea
        self.state_store = state_store

    def persist_new_states(self, states: list[ExecutionRuntimeState]) -> None:
        for state in states:
            self.state_store.save(state)

    def run_cycle(self, *, execution_id, last_price=None):
        state = self.state_store.load(execution_id)
        if state is None:
            raise KeyError(f"Execution {execution_id} not found.")
        result = self.tea.run_cycle(state=state, last_price=last_price)
        self.state_store.save(state)
        return result
