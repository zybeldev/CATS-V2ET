from uuid import uuid4

from cats.trace import TraceService


def test_trace_records_provenance_lineage_and_events():
    trace = TraceService()
    flow_id = uuid4()
    assessment_id = uuid4()
    evidence_id = uuid4()
    decision_id = uuid4()

    p = trace.add_provenance(
        target_entity_type="TAA_Assessment",
        target_entity_id=assessment_id,
        source_entity_type="TAA_Evidence_Item",
        source_entity_id=evidence_id,
        relationship_type="SUPPORTED_BY",
    )
    l = trace.add_lineage(
        flow_id=flow_id,
        parent_entity_type="TAA_Assessment",
        parent_entity_id=assessment_id,
        child_entity_type="PMA_Portfolio_Decision",
        child_entity_id=decision_id,
        relationship_type="INFORMED",
        sequence_number=1,
    )
    e = trace.record_event(
        flow_id=flow_id,
        event_type="PORTFOLIO_DECISION_CREATED",
        source_component="PMA",
        entity_type="PMA_Portfolio_Decision",
        entity_id=decision_id,
        status="FINAL",
    )

    assert p.target_entity_id == assessment_id
    assert l.flow_id == flow_id
    assert e.source_component == "PMA"
    assert len(trace.provenance_links) == 1
    assert len(trace.lineage_links) == 1
    assert len(trace.events) == 1
