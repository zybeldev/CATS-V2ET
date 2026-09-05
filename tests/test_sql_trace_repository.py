from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.database.base import Base
import cats.database.models as models
from cats.trace import PersistentTraceService, SQLTraceRepository


def test_sql_trace_persists_event_provenance_and_lineage():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        trace = PersistentTraceService(SQLTraceRepository(session))
        flow_id = uuid4()
        evidence_id = uuid4()
        assessment_id = uuid4()
        decision_id = uuid4()

        trace.add_provenance(
            target_entity_type="TAA_Assessment",
            target_entity_id=assessment_id,
            source_entity_type="TAA_Evidence_Item",
            source_entity_id=evidence_id,
            relationship_type="SUPPORTED_BY",
        )
        trace.add_lineage(
            flow_id=flow_id,
            parent_entity_type="TAA_Assessment",
            parent_entity_id=assessment_id,
            child_entity_type="PMA_Portfolio_Decision",
            child_entity_id=decision_id,
            relationship_type="INFORMED",
            sequence_number=1,
        )
        trace.record_event(
            flow_id=flow_id,
            event_type="DECISION_CREATED",
            source_component="PMA",
            entity_type="PMA_Portfolio_Decision",
            entity_id=decision_id,
            status="FINAL",
        )

        assert session.query(models.TraceProvenanceLinkRecord).count() == 1
        assert session.query(models.TraceLineageLinkRecord).count() == 1
        assert session.query(models.TraceEventRecord).count() == 1
