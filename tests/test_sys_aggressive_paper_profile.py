from uuid import uuid4

import pytest

from cats.contracts import DecisionTarget, PortfolioDecision
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext


def _decision():
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
                target_weight=0.20,
                target_quantity=10,
            )
        ],
        rationale_summary="test",
    )
    return decision, instrument_id, config_id


def test_normal_profile_preserves_existing_limits(monkeypatch):
    monkeypatch.delenv("CATS_SYS_PROFILE", raising=False)
    config = GovernedConfiguration(
        configuration_version_id=str(uuid4()),
        environment_code="PAPER",
        max_position_weight=0.10,
        max_total_equity_exposure=0.95,
        min_cash_reserve_weight=0.05,
    )
    assert config.max_position_weight == 0.10
    assert config.max_total_equity_exposure == 0.95
    assert config.min_cash_reserve_weight == 0.05


def test_aggressive_profile_relaxes_bounded_paper_limits(monkeypatch):
    monkeypatch.setenv("CATS_SYS_PROFILE", "AGGRESSIVE_PAPER_TEST")
    config = GovernedConfiguration(
        configuration_version_id=str(uuid4()),
        environment_code="PAPER",
        max_position_weight=0.10,
        max_total_equity_exposure=0.95,
        min_cash_reserve_weight=0.05,
    )
    assert config.max_position_weight == 0.25
    assert config.max_total_equity_exposure == 0.99
    assert config.min_cash_reserve_weight == 0.01
    assert config.max_order_value == 50_000.0
    assert config.max_order_quantity == 5_000.0


def test_aggressive_profile_refuses_non_paper(monkeypatch):
    monkeypatch.setenv("CATS_SYS_PROFILE", "AGGRESSIVE_PAPER_TEST")
    with pytest.raises(ValueError, match="only with PAPER"):
        GovernedConfiguration(
            configuration_version_id=str(uuid4()),
            environment_code="PROD",
            permitted_trading_environment="PROD",
        )


def test_aggressive_profile_does_not_bypass_direction_guard(monkeypatch):
    monkeypatch.setenv("CATS_SYS_PROFILE", "AGGRESSIVE_PAPER_TEST")
    decision, instrument_id, config_id = _decision()
    config = GovernedConfiguration(
        configuration_version_id=str(config_id),
        environment_code="PAPER",
        max_position_weight=0.10,
        max_total_equity_exposure=0.95,
        min_cash_reserve_weight=0.05,
    )
    context = ValidationContext(
        environment_code="PAPER",
        buying_power=100_000,
        cash_weight=0.20,
        current_total_equity_exposure=0.80,
        instrument_types={instrument_id: "EQUITY"},
        estimated_order_values={instrument_id: 100.0},
        estimated_order_quantities={instrument_id: -0.0605967538},
    )

    result = SystemValidator().validate(decision, config, context)
    assert result.result == "FAIL"
    direction_rule = next(
        rule
        for rule in result.rule_results
        if rule.rule_code == "DECISION_DIRECTION_CONSISTENCY"
    )
    assert direction_rule.result == "FAIL"
