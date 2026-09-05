from __future__ import annotations

import json
from sqlalchemy.orm import Session

from cats.database import models
from .service import LineageLink, ProvenanceLink, TraceEvent


class SQLTraceRepository:
    """Persists material TRACE records without changing their authority semantics."""

    def __init__(self, session: Session):
        self.session = session

    def save_event(self, event: TraceEvent) -> None:
        self.session.add(
            models.TraceEventRecord(
                event_id=str(event.event_id),
                flow_id=str(event.flow_id),
                event_type=event.event_type,
                source_component=event.source_component,
                entity_type=event.entity_type,
                entity_id=str(event.entity_id),
                occurred_at=event.occurred_at,
                status=event.status,
                payload_json=json.dumps(event.payload, default=str, sort_keys=True),
            )
        )

    def save_provenance(self, link: ProvenanceLink) -> None:
        self.session.add(
            models.TraceProvenanceLinkRecord(
                provenance_link_id=str(link.provenance_link_id),
                target_entity_type=link.target_entity_type,
                target_entity_id=str(link.target_entity_id),
                source_entity_type=link.source_entity_type,
                source_entity_id=str(link.source_entity_id),
                relationship_type=link.relationship_type,
                created_at=link.created_at,
            )
        )

    def save_lineage(self, link: LineageLink) -> None:
        self.session.add(
            models.TraceLineageLinkRecord(
                lineage_link_id=str(link.lineage_link_id),
                flow_id=str(link.flow_id),
                parent_entity_type=link.parent_entity_type,
                parent_entity_id=str(link.parent_entity_id),
                child_entity_type=link.child_entity_type,
                child_entity_id=str(link.child_entity_id),
                relationship_type=link.relationship_type,
                sequence_number=link.sequence_number,
                created_at=link.created_at,
            )
        )

    def commit(self) -> None:
        self.session.commit()
