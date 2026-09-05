from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from cats.database import models


def utc_now():
    return datetime.now(timezone.utc)


class AcceptedPortfolioStateRepository:
    """Persists PMA's accepted broker-confirmed Portfolio State.

    This repository never accepts inferred execution state. The caller must
    provide broker-confirmed account and position facts after reconciliation.
    """

    def __init__(self, session: Session):
        self.session = session

    def persist_broker_confirmed_state(
        self,
        *,
        portfolio_id: UUID,
        prior_portfolio_state_id: UUID,
        source_portfolio_decision_id: UUID,
        configuration_version_id: UUID,
        cash: float,
        equity: float,
        buying_power: float,
        positions: list[dict],
    ) -> UUID:
        if equity <= 0:
            raise ValueError("Broker-confirmed equity must be positive.")

        capital_state_id = uuid4()
        portfolio_state_id = uuid4()
        now = utc_now()

        self.session.add(
            models.CapitalState(
                capital_state_id=str(capital_state_id),
                portfolio_id=str(portfolio_id),
                prior_capital_state_id=None,
                cash=float(cash),
                net_liquidation_value=float(equity),
                buying_power=float(buying_power),
                margin_used=0.0,
                leverage=0.0,
                currency="USD",
                effective_at=now,
            )
        )
        self.session.flush()
        self.session.add(
            models.PortfolioState(
                portfolio_state_id=str(portfolio_state_id),
                portfolio_id=str(portfolio_id),
                prior_portfolio_state_id=str(prior_portfolio_state_id),
                source_portfolio_decision_id=str(source_portfolio_decision_id),
                configuration_version_id=str(configuration_version_id),
                capital_state_id=str(capital_state_id),
                effective_at=now,
                status="ACCEPTED",
            )
        )

        self.session.flush()

        for fact in positions:
            quantity = float(fact["quantity"])
            if abs(quantity) < 1e-12:
                continue
            self.session.add(
                models.Position(
                    portfolio_state_id=str(portfolio_state_id),
                    financial_instrument_id=str(fact["financial_instrument_id"]),
                    quantity=quantity,
                    average_cost=(
                        None if fact.get("average_cost") is None else float(fact["average_cost"])
                    ),
                    market_value=(
                        None if fact.get("market_value") is None else float(fact["market_value"])
                    ),
                    currency=fact.get("currency", "USD"),
                    status="OPEN",
                )
            )

        self.session.commit()
        return portfolio_state_id
