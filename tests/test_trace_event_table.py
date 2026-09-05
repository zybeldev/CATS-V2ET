from cats.database.base import Base
import cats.database.models  # noqa


def test_trace_event_table_registered():
    assert "TRACE_Event" in Base.metadata.tables
