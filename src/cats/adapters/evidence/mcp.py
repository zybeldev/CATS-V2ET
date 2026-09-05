from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from cats.adapters.mcp import MCPToolClient
from cats.retrieval.models import EvidenceDocument

from .public import PublicEvidenceRequest


class MCPPublicEvidenceSource:
    """TAA evidence ingestion through an MCP tool boundary.

    This connector is deliberately limited to latency-tolerant public evidence.
    It does not expose broker execution, Portfolio intent, or other CATS
    authority through MCP.
    """

    TOOL_NAME = "fetch_public_evidence"

    def __init__(self, client: MCPToolClient):
        self.client = client

    def ingest(self, request: PublicEvidenceRequest) -> EvidenceDocument:
        payload = self.client.call_tool(
            self.TOOL_NAME,
            {
                "url": request.url,
                "source_name": request.source_name,
                "financial_instrument_id": (
                    None
                    if request.financial_instrument_id is None
                    else str(request.financial_instrument_id)
                ),
                "observed_at": (
                    None if request.observed_at is None else request.observed_at.isoformat()
                ),
            },
        )
        data = self._coerce_mapping(payload)
        text = str(data.get("text", "")).strip()
        if not text:
            raise ValueError("MCP public evidence tool returned no usable text")

        financial_instrument_id = self._optional_uuid(data.get("financial_instrument_id"))
        observed_at = self._optional_datetime(data.get("observed_at"))
        retrieved_at = self._optional_datetime(data.get("retrieved_at"))
        metadata = dict(data.get("metadata") or {})
        metadata.setdefault("connector", "MCP")
        metadata.setdefault("mcp_tool", self.TOOL_NAME)

        kwargs: dict[str, Any] = {
            "text": text,
            "source_name": str(data.get("source_name") or request.source_name),
            "external_reference": data.get("external_reference") or request.url,
            "financial_instrument_id": financial_instrument_id,
            "observed_at": observed_at,
            "metadata": metadata,
        }
        if retrieved_at is not None:
            kwargs["retrieved_at"] = retrieved_at
        return EvidenceDocument(**kwargs)

    @staticmethod
    def _coerce_mapping(payload: Any) -> Mapping[str, Any]:
        if isinstance(payload, Mapping):
            # FastMCP may place a dictionary under a single structured-content key.
            if "result" in payload and isinstance(payload["result"], Mapping):
                return payload["result"]
            return payload
        raise TypeError("MCP public evidence tool must return a structured mapping")

    @staticmethod
    def _optional_uuid(value: Any) -> UUID | None:
        if value in (None, ""):
            return None
        return UUID(str(value))

    @staticmethod
    def _optional_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
