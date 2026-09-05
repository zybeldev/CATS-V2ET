from uuid import uuid4

from cats.contracts import OptimizationRequest
from cats.services.pms import EquityCandidate, EquityOptimizationConstraints, PMAOptimizerAdapter


def test_pma_optimizer_adapter_materializes_target_quantity():
    instrument_id = uuid4()
    request = OptimizationRequest(
        flow_id=uuid4(),
        source="PMA",
        destination="PMS",
        optimization_request_id=uuid4(),
        portfolio_id=uuid4(),
        source_portfolio_state_id=uuid4(),
        strategic_envelope_id=uuid4(),
        configuration_version_id=uuid4(),
        assessment_ids=[uuid4()],
        requested_model="V2E_CONSTRAINED_EQUITY",
        status="REQUESTED",
    )
    alt = PMAOptimizerAdapter().optimize(
        request,
        candidates=[EquityCandidate(instrument_id, score=1.0)],
        constraints=EquityOptimizationConstraints(0.10, 0.95, 0.05),
        portfolio_value=10_000,
        prices_by_instrument={instrument_id: 100.0},
    )
    assert alt.feasibility_status == "FEASIBLE"
    assert alt.positions[0].target_weight == 0.10
    assert alt.positions[0].target_quantity == 10.0
