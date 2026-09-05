from uuid import uuid4

from cats.contracts import DecisionTarget, PortfolioDecision
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext


def make_decision(weight=0.10):
    instrument_id = uuid4()
    config_id = uuid4()
    decision = PortfolioDecision(
        flow_id=uuid4(),
        source="PMA",
        destination="SYS",
        portfolio_decision_id=uuid4(),
        portfolio_id=uuid4(),
        source_portfolio_state_id=uuid4(),
        configuration_version_id=config_id,
        decision_type="BUY_OR_INCREASE",
        horizon="TACTICAL",
        strategic_envelope_id=uuid4(),
        targets=[
            DecisionTarget(
                financial_instrument_id=instrument_id,
                target_weight=weight,
                target_quantity=10,
            )
        ],
        rationale_summary="test",
    )
    return decision, instrument_id, config_id


def test_sys_passes_valid_equity_decision():
    decision, instrument_id, config_id = make_decision()
    config = GovernedConfiguration(
        configuration_version_id=str(config_id),
        environment_code="PAPER",
    )
    context = ValidationContext(
        environment_code="PAPER",
        buying_power=100_000,
        cash_weight=0.20,
        current_total_equity_exposure=0.80,
        instrument_types={instrument_id: "EQUITY"},
        estimated_order_values={instrument_id: 1_000},
        estimated_order_quantities={instrument_id: 10},
    )

    result = SystemValidator().validate(decision, config, context)
    assert result.result == "PASS"
    assert result.destination == "TEA"


def test_sys_fails_closed_on_concentration_violation():
    decision, instrument_id, config_id = make_decision(weight=0.50)
    config = GovernedConfiguration(
        configuration_version_id=str(config_id),
        environment_code="PAPER",
        max_position_weight=0.25,
    )
    context = ValidationContext(
        environment_code="PAPER",
        buying_power=100_000,
        cash_weight=0.20,
        current_total_equity_exposure=0.80,
        instrument_types={instrument_id: "EQUITY"},
        estimated_order_values={instrument_id: 1_000},
        estimated_order_quantities={instrument_id: 10},
    )

    result = SystemValidator().validate(decision, config, context)
    assert result.result == "FAIL"
    assert result.destination == "PMA"


def test_sys_fails_closed_when_buy_decision_requires_sell_delta():
    decision, instrument_id, config_id = make_decision()
    config = GovernedConfiguration(
        configuration_version_id=str(config_id),
        environment_code="PAPER",
    )
    context = ValidationContext(
        environment_code="PAPER",
        buying_power=100_000,
        cash_weight=0.20,
        current_total_equity_exposure=0.80,
        instrument_types={instrument_id: "EQUITY"},
        estimated_order_values={instrument_id: 100},
        estimated_order_quantities={instrument_id: -0.0605967538},
    )

    result = SystemValidator().validate(decision, config, context)

    assert result.result == "FAIL"
    direction_rule = next(
        rule for rule in result.rule_results
        if rule.rule_code == "DECISION_DIRECTION_CONSISTENCY"
    )
    assert direction_rule.result == "FAIL"
