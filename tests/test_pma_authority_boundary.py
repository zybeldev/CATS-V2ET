from cats.contracts import PortfolioAlternative, PortfolioDecision


def test_contracts_preserve_pma_pms_boundary():
    assert "positions" in PortfolioAlternative.model_fields
    assert "selected_portfolio_alternative_id" in PortfolioDecision.model_fields
    assert "targets" in PortfolioDecision.model_fields
