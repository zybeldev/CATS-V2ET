from cats.database.base import Base
import cats.database.models  # noqa


def test_step15_broker_audit_tables_registered():
    assert "TEA_Reconciliation" in Base.metadata.tables
    assert "TES_Fill" in Base.metadata.tables
