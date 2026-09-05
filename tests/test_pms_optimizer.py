from uuid import uuid4

from cats.services.pms import (
    DeterministicEquityOptimizer,
    EquityCandidate,
    EquityOptimizationConstraints,
)


def test_optimizer_is_deterministic_and_respects_constraints():
    ids = [uuid4(), uuid4(), uuid4()]
    candidates = [
        EquityCandidate(ids[0], score=3.0, expected_return=0.12, expected_risk=0.20),
        EquityCandidate(ids[1], score=2.0, expected_return=0.10, expected_risk=0.18),
        EquityCandidate(ids[2], score=1.0, expected_return=0.08, expected_risk=0.15),
    ]
    constraints = EquityOptimizationConstraints(
        max_position_weight=0.40,
        max_total_equity_exposure=0.90,
        min_cash_reserve_weight=0.10,
    )
    optimizer = DeterministicEquityOptimizer()
    kwargs = dict(
        flow_id=uuid4(),
        source="PMS",
        destination="PMA",
        optimization_run_id=uuid4(),
        configuration_version_id=uuid4(),
        candidates=candidates,
        constraints=constraints,
    )
    a = optimizer.optimize(**kwargs)
    b = optimizer.optimize(**kwargs)

    assert a.feasibility_status == "FEASIBLE"
    assert [(p.financial_instrument_id, p.target_weight) for p in a.positions] == [
        (p.financial_instrument_id, p.target_weight) for p in b.positions
    ]
    assert sum(p.target_weight for p in a.positions) <= 0.90 + 1e-9
    assert all(p.target_weight <= 0.40 + 1e-9 for p in a.positions)


def test_optimizer_returns_explicit_infeasible_result():
    result = DeterministicEquityOptimizer().optimize(
        flow_id=uuid4(),
        source="PMS",
        destination="PMA",
        optimization_run_id=uuid4(),
        configuration_version_id=uuid4(),
        candidates=[EquityCandidate(uuid4(), score=0.0)],
        constraints=EquityOptimizationConstraints(0.25, 0.90, 0.10),
    )
    assert result.feasibility_status == "INFEASIBLE"
    assert result.positions == []
