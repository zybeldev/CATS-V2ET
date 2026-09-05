from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.database.base import Base
from cats.database import models
from cats.repositories.flow_audit import FlowAuditRepository


def test_empty_flow_audit_reports_missing_material_stages():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        summary = FlowAuditRepository(session).summarize("missing-flow")
        assert summary.complete is False
        assert "assessment" in summary.missing_stages
        assert "execution" in summary.missing_stages
        assert "accepted_portfolio_state" in summary.missing_stages
