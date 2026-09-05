from uuid import uuid4

import pytest
from pydantic import ValidationError

from cats.contracts import (
    BrokerExecutionResult,
    PortfolioDecision,
    ValidationResult,
)


def test_portfolio_decision_requires_source_state():
    with pytest.raises(ValidationError):
        PortfolioDecision(
            flow_id=uuid4(),
            source="PMA",
            destination="SYS",
            portfolio_decision_id=uuid4(),
            portfolio_id=uuid4(),
            decision_type="REBALANCE",
            horizon="TACTICAL",
            strategic_envelope_id=uuid4(),
            rationale_summary="test",
        )


def test_validation_result_is_explicit_pass_or_fail():
    result = ValidationResult(
        flow_id=uuid4(),
        source="SYS",
        destination="TEA",
        validation_result_id=uuid4(),
        portfolio_decision_id=uuid4(),
        result="PASS",
    )
    assert result.result == "PASS"


def test_broker_result_can_preserve_unknown_outcome():
    result = BrokerExecutionResult(
        flow_id=uuid4(),
        source="TES",
        destination="TEA",
        execution_action_id=uuid4(),
        execution_id=uuid4(),
        certainty_status="UNKNOWN_OUTCOME",
    )
    assert result.certainty_status == "UNKNOWN_OUTCOME"
