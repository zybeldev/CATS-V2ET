from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from cats.database import models


def utc_now():
    return datetime.now(timezone.utc)


class SQLTraceService:
    """SQL-backed TRACE persistence using generic cross-domain records."""

    def __init__(self, session: Session):
        self.session = session

    def record_event(self, *, flow_id: UUID, event_type: str, source_component: str,
                     entity_type: str, entity_id: UUID, status: str, payload=None):
        row = models.TraceEventRecord(
            event_id=str(uuid4()),
            flow_id=str(flow_id),
            event_type=event_type,
            source_component=source_component,
            entity_type=entity_type,
            entity_id=str(entity_id),
            occurred_at=utc_now(),
            status=status,
            payload_json=None if payload is None else str(payload),
        )
        self.session.add(row)
        self.session.commit()
        return row
