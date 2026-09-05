from cats.database.base import Base
import cats.database.models  # noqa


def test_trace_material_tables_registered():
    assert "TRACE_Event" in Base.metadata.tables
    assert "TRACE_Provenance_Link" in Base.metadata.tables
    assert "TRACE_Lineage_Link" in Base.metadata.tables
