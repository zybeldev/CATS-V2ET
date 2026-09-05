from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.adapters.alpaca.models import BrokerActionOutcome, BrokerOrder
from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.contracts import DecisionTarget, PortfolioDecision, ValidationResult
from cats.database import models
from cats.database.base import Base
from cats.runtime.recovery import RecoveryCoordinator
from cats.runtime.sql_store import SQLExecutionStateStore
from cats.systems.tes import TradingExecutionSystem


class ControlledBroker:
    """Broker double used to force an unknown submission outcome and controlled reconciliation."""

    def __init__(self) -> None:
        self.submissions = 0
        self.reconciliation_order: BrokerOrder | None = None

    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        self.submissions += 1
        return BrokerActionOutcome(
            "UNKNOWN_OUTCOME",
            error_code="TIMEOUT",
            error_message="Synthetic broker timeout for Step 07B.",
        )

    def get_order_by_client_order_id(self, client_order_id):
        return self.reconciliation_order


def _seed_dependencies(
    session: Session,
    *,
    environment_id: str,
    flow_id: str,
    instrument_id: UUID,
    portfolio_id: UUID,
    decision_id: UUID,
) -> tuple[str, str, str]:
    config_id = str(uuid4())
    capital_id = str(uuid4())
    state_id = str(uuid4())
    envelope_id = str(uuid4())
    now = datetime.now(timezone.utc)

    session.add(
        models.Environment(
            environment_id=environment_id,
            environment_code="PAPER",
            name="Step 07B PAPER",
            is_active=True,
        )
    )
    session.add(
        models.FinancialInstrument(
            financial_instrument_id=str(instrument_id),
            instrument_type="EQUITY",
            symbol="ACME",
            status="ACTIVE",
        )
    )
    session.add(
        models.TraceFlow(
            flow_id=flow_id,
            environment_id=environment_id,
            flow_type="SYSTEM_ASSURANCE_TEST",
            started_at=now,
            status="ACTIVE",
        )
    )
    session.add(
        models.ConfigurationVersion(
            configuration_version_id=config_id,
            environment_id=environment_id,
            version_number=1,
            effective_at=now,
            status="ACTIVE",
            is_current=True,
        )
    )
    session.add(
        models.Portfolio(
            portfolio_id=str(portfolio_id),
            environment_id=environment_id,
            name="Step 07B Portfolio",
            status="ACTIVE",
        )
    )
    session.add(
        models.StrategicEnvelope(
            strategic_envelope_id=envelope_id,
            configuration_version_id=config_id,
            portfolio_id=str(portfolio_id),
            effective_at=now,
            status="ACTIVE",
        )
    )
    session.add(
        models.CapitalState(
            capital_state_id=capital_id,
            portfolio_id=str(portfolio_id),
            cash=10000,
            net_liquidation_value=10000,
            buying_power=10000,
            effective_at=now,
        )
    )
    session.add(
        models.PortfolioState(
            portfolio_state_id=state_id,
            portfolio_id=str(portfolio_id),
            configuration_version_id=config_id,
            capital_state_id=capital_id,
            effective_at=now,
            status="CURRENT",
        )
    )
    session.flush()
    session.add(
        models.PortfolioDecisionRecord(
            portfolio_decision_id=str(decision_id),
            portfolio_id=str(portfolio_id),
            source_portfolio_state_id=state_id,
            decision_type="BUY_OR_INCREASE",
            decision_horizon="TACTICAL",
            configuration_version_id=config_id,
            strategic_envelope_id=envelope_id,
            flow_id=flow_id,
            created_at=now,
            status="FINAL",
            rationale_summary="Step 07B controlled assurance scenario.",
        )
    )
    session.flush()
    return config_id, envelope_id, state_id


def _make_decision_validation(
    *,
    flow_id: str,
    portfolio_id: UUID,
    decision_id: UUID,
    instrument_id: UUID,
    config_id: str,
    envelope_id: str,
    state_id: str,
) -> tuple[PortfolioDecision, ValidationResult]:
    decision = PortfolioDecision(
        flow_id=UUID(flow_id),
        source="PMA",
        destination="SYS",
        portfolio_decision_id=decision_id,
        portfolio_id=portfolio_id,
        source_portfolio_state_id=UUID(state_id),
        configuration_version_id=UUID(config_id),
        decision_type="BUY_OR_INCREASE",
        horizon="TACTICAL",
        strategic_envelope_id=UUID(envelope_id),
        targets=[DecisionTarget(financial_instrument_id=instrument_id, target_quantity=5)],
        rationale_summary="Step 07B controlled assurance scenario.",
        status="FINAL",
    )
    validation = ValidationResult(
        flow_id=decision.flow_id,
        source="SYS",
        destination="TEA",
        validation_result_id=uuid4(),
        portfolio_decision_id=decision.portfolio_decision_id,
        configuration_version_id=decision.configuration_version_id,
        result="PASS",
        status="FINAL",
    )
    return decision, validation


def _create_persisted_unknown_outcome(engine, broker: ControlledBroker) -> dict:
    environment_id = str(uuid4())
    flow_id = str(uuid4())
    instrument_id = uuid4()
    portfolio_id = uuid4()
    decision_id = uuid4()

    with Session(engine) as session:
        config_id, envelope_id, state_id = _seed_dependencies(
            session,
            environment_id=environment_id,
            flow_id=flow_id,
            instrument_id=instrument_id,
            portfolio_id=portfolio_id,
            decision_id=decision_id,
        )
        decision, validation = _make_decision_validation(
            flow_id=flow_id,
            portfolio_id=portfolio_id,
            decision_id=decision_id,
            instrument_id=instrument_id,
            config_id=config_id,
            envelope_id=envelope_id,
            state_id=state_id,
        )

        agent = TradingExecutionAgent(
            DeterministicTEAReasoningModel(),
            TradingExecutionSystem(broker),
        )
        state = agent.start_execution(
            decision=decision,
            validation=validation,
            symbol_by_instrument={instrument_id: "ACME"},
        )[0]

        first = agent.run_cycle(state=state, last_price=100.0)
        if first is None or first.certainty_status != "UNKNOWN_OUTCOME":
            raise AssertionError("Controlled submission did not produce UNKNOWN_OUTCOME.")

        # A second TEA cycle must reconcile, not submit another market order.
        second = agent.run_cycle(state=state, last_price=100.0)
        if second is not None:
            raise AssertionError("Expected unresolved reconciliation to remain non-terminal.")
        if broker.submissions != 1:
            raise AssertionError("Unknown outcome caused a blind duplicate submission.")

        store = SQLExecutionStateStore(
            session,
            environment_id=environment_id,
            flow_id=flow_id,
        )
        store.save(state)

        return {
            "environment_id": environment_id,
            "flow_id": flow_id,
            "execution_id": state.execution_id,
            "client_order_id": state.client_order_id,
            "target_quantity": state.target_quantity,
            "submissions": broker.submissions,
        }


def _run_resolved_scenario(db_path: Path) -> dict:
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(engine)
    broker = ControlledBroker()
    identity = _create_persisted_unknown_outcome(engine, broker)

    broker.reconciliation_order = BrokerOrder(
        broker_order_id="BROKER-FILLED-1",
        client_order_id=identity["client_order_id"],
        symbol="ACME",
        side="BUY",
        quantity=identity["target_quantity"],
        order_type="MARKET",
        status="FILLED",
        filled_quantity=identity["target_quantity"],
        average_fill_price=100.0,
    )

    # New Session + new store instance demonstrates recovery from persisted state.
    with Session(engine) as session:
        store = SQLExecutionStateStore(
            session,
            environment_id=identity["environment_id"],
            flow_id=identity["flow_id"],
        )
        before = store.load(identity["execution_id"])
        if before is None:
            raise AssertionError("Persisted execution could not be reconstructed.")

        results = RecoveryCoordinator(
            store,
            TradingExecutionSystem(broker),
        ).recover_active_executions()
        after = store.load(identity["execution_id"])

    if after is None:
        raise AssertionError("Recovered execution could not be loaded.")

    return {
        "unknown_outcome_detected": before.certainty_status == "UNKNOWN_OUTCOME",
        "client_order_id_preserved": before.client_order_id == identity["client_order_id"],
        "blind_resubmission_prevented": broker.submissions == 1,
        "recovered_certainty": results[0].recovered_certainty,
        "final_status": after.status,
        "remaining_quantity": after.remaining_quantity,
        "passed": (
            before.certainty_status == "UNKNOWN_OUTCOME"
            and before.client_order_id == identity["client_order_id"]
            and broker.submissions == 1
            and results[0].recovered_certainty == "CONFIRMED"
            and after.status == "COMPLETED"
            and after.remaining_quantity == 0
        ),
    }


def _run_unresolved_scenario(db_path: Path) -> dict:
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(engine)
    broker = ControlledBroker()
    identity = _create_persisted_unknown_outcome(engine, broker)

    with Session(engine) as session:
        store = SQLExecutionStateStore(
            session,
            environment_id=identity["environment_id"],
            flow_id=identity["flow_id"],
        )
        before = store.load(identity["execution_id"])
        if before is None:
            raise AssertionError("Persisted execution could not be reconstructed.")

        results = RecoveryCoordinator(
            store,
            TradingExecutionSystem(broker),
        ).recover_active_executions()
        after = store.load(identity["execution_id"])

    if after is None:
        raise AssertionError("Recovered execution could not be loaded.")

    return {
        "unknown_outcome_detected": before.certainty_status == "UNKNOWN_OUTCOME",
        "blind_resubmission_prevented": broker.submissions == 1,
        "recovered_certainty": results[0].recovered_certainty,
        "final_status": after.status,
        "passed": (
            before.certainty_status == "UNKNOWN_OUTCOME"
            and broker.submissions == 1
            and results[0].recovered_certainty == "UNKNOWN_OUTCOME"
            and after.status == "SUSPENDED"
        ),
    }


def run_evaluation() -> dict:
    with tempfile.TemporaryDirectory(prefix="cats-v2et-step07b-") as tmp:
        root = Path(tmp)
        resolved = _run_resolved_scenario(root / "resolved.db")
        unresolved = _run_unresolved_scenario(root / "unresolved.db")

    result = {
        "experiment": "CATS V2ET Step 07B - System Assurance Failure and Recovery",
        "resolved_broker_reality": resolved,
        "unresolved_broker_reality": unresolved,
        "checks": {
            "detects_unknown_outcome": (
                resolved["unknown_outcome_detected"]
                and unresolved["unknown_outcome_detected"]
            ),
            "prevents_blind_resubmission": (
                resolved["blind_resubmission_prevented"]
                and unresolved["blind_resubmission_prevented"]
            ),
            "preserves_recovery_identity": resolved["client_order_id_preserved"],
            "resolves_confirmed_fill_to_completed": (
                resolved["recovered_certainty"] == "CONFIRMED"
                and resolved["final_status"] == "COMPLETED"
            ),
            "suspends_when_reality_remains_unknown": (
                unresolved["recovered_certainty"] == "UNKNOWN_OUTCOME"
                and unresolved["final_status"] == "SUSPENDED"
            ),
        },
    }
    result["result"] = "PASS" if all(result["checks"].values()) else "FAIL"
    return result


def main() -> None:
    result = run_evaluation()

    print("CATS V2ET STEP 07B — SYSTEM ASSURANCE FAILURE / RECOVERY")
    print("=" * 72)
    print("\nResolved broker reality:")
    print(json.dumps(result["resolved_broker_reality"], indent=2))
    print("\nUnresolved broker reality:")
    print(json.dumps(result["unresolved_broker_reality"], indent=2))
    print("\nChecks:")
    for key, passed in result["checks"].items():
        print(f"  {key}: {passed}")
    print(f"\nSTEP 07B RESULT: {result['result']}")

    output = Path("CATS_V2ET_Step_07B_System_Assurance_Failure_Recovery_Result.json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved evaluation record: {output}")


if __name__ == "__main__":
    main()
