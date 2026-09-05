from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def evidence_age_seconds(document: "EvidenceDocument", *, as_of: datetime | None = None) -> float | None:
    """Return source age from observed/source date to the supplied evaluation time.

    For public evidence in V2ET, ``observed_at`` is the source publication or
    source-observation time when one can be established. ``retrieved_at`` is
    intentionally not used as a substitute for source freshness.
    """

    if document.observed_at is None:
        return None
    reference = _as_utc(as_of or utc_now())
    observed = _as_utc(document.observed_at)
    return (reference - observed).total_seconds()


def evidence_freshness_status(
    document: "EvidenceDocument", *, as_of: datetime | None = None
) -> str:
    """Classify source age without declaring whether the evidence is valid.

    The categories are observability metadata. TAA still evaluates whether age
    is acceptable for the requested STRATEGIC or TACTICAL horizon.
    """

    age_seconds = evidence_age_seconds(document, as_of=as_of)
    if age_seconds is None:
        return "SOURCE_DATE_UNKNOWN"
    if age_seconds < -3600:
        return "SOURCE_DATE_IN_FUTURE"
    age_days = max(0.0, age_seconds / 86400.0)
    if age_days <= 1:
        return "SAME_DAY"
    if age_days <= 7:
        return "RECENT_7D"
    if age_days <= 30:
        return "AGING_30D"
    return "HISTORICAL"


@dataclass(frozen=True)
class EvidenceDocument:
    text: str
    source_name: str
    external_reference: str | None = None
    financial_instrument_id: UUID | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_document_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class RetrievedEvidence:
    document: EvidenceDocument
    score: float
    rank: int


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    purpose: str
    financial_instrument_id: UUID | None = None
    top_k: int = 5

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Retrieval query text cannot be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
