from __future__ import annotations

from .service import TraceService
from .sql_repository import SQLTraceRepository


class PersistentTraceService(TraceService):
    """TRACE service that writes each material record to SQL."""

    def __init__(self, repository: SQLTraceRepository):
        super().__init__()
        self.repository = repository

    def add_provenance(self, **kwargs):
        link = super().add_provenance(**kwargs)
        self.repository.save_provenance(link)
        self.repository.commit()
        return link

    def add_lineage(self, **kwargs):
        link = super().add_lineage(**kwargs)
        self.repository.save_lineage(link)
        self.repository.commit()
        return link

    def record_event(self, **kwargs):
        event = super().record_event(**kwargs)
        self.repository.save_event(event)
        self.repository.commit()
        return event
