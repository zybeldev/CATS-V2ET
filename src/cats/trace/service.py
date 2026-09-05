from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProvenanceLink:
    provenance_link_id: UUID
    target_entity_type: str
    target_entity_id: UUID
    source_entity_type: str
    source_entity_id: UUID
    relationship_type: str
    created_at: datetime


@dataclass(frozen=True)
class LineageLink:
    lineage_link_id: UUID
    flow_id: UUID
    parent_entity_type: str
    parent_entity_id: UUID
    child_entity_type: str
    child_entity_id: UUID
    relationship_type: str
    sequence_number: int
    created_at: datetime


@dataclass(frozen=True)
class TraceEvent:
    event_id: UUID
    flow_id: UUID
    event_type: str
    source_component: str
    entity_type: str
    entity_id: UUID
    occurred_at: datetime
    status: str
    payload: dict[str, Any]


class TraceService:
    """In-memory trace facade for the V2E vertical slice.

    Repository persistence can replace this facade without changing the
    provenance/lineage contract.
    """

    def __init__(self):
        self.provenance_links: list[ProvenanceLink] = []
        self.lineage_links: list[LineageLink] = []
        self.events: list[TraceEvent] = []

    def add_provenance(
        self,
        *,
        target_entity_type: str,
        target_entity_id: UUID,
        source_entity_type: str,
        source_entity_id: UUID,
        relationship_type: str,
    ) -> ProvenanceLink:
        link = ProvenanceLink(
            provenance_link_id=uuid4(),
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            relationship_type=relationship_type,
            created_at=utc_now(),
        )
        self.provenance_links.append(link)
        return link

    def add_lineage(
        self,
        *,
        flow_id: UUID,
        parent_entity_type: str,
        parent_entity_id: UUID,
        child_entity_type: str,
        child_entity_id: UUID,
        relationship_type: str,
        sequence_number: int,
    ) -> LineageLink:
        link = LineageLink(
            lineage_link_id=uuid4(),
            flow_id=flow_id,
            parent_entity_type=parent_entity_type,
            parent_entity_id=parent_entity_id,
            child_entity_type=child_entity_type,
            child_entity_id=child_entity_id,
            relationship_type=relationship_type,
            sequence_number=sequence_number,
            created_at=utc_now(),
        )
        self.lineage_links.append(link)
        return link

    def record_event(
        self,
        *,
        flow_id: UUID,
        event_type: str,
        source_component: str,
        entity_type: str,
        entity_id: UUID,
        status: str,
        payload: dict[str, Any] | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            event_id=uuid4(),
            flow_id=flow_id,
            event_type=event_type,
            source_component=source_component,
            entity_type=entity_type,
            entity_id=entity_id,
            occurred_at=utc_now(),
            status=status,
            payload=payload or {},
        )
        self.events.append(event)
        return event
