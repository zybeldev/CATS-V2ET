from __future__ import annotations

from dataclasses import asdict
from sqlalchemy.orm import Session

from cats.database import models
from cats.repositories.flow_audit import FlowAuditRepository


class PostRunVerificationError(RuntimeError):
    pass


class PostRunVerifier:
    """Fail-closed verification for a completed PAPER flow."""

    def __init__(self, session: Session):
        self.session = session
        self.audit = FlowAuditRepository(session)

    def verify(self, flow_id: str) -> dict:
        flow = self.session.get(models.TraceFlow, flow_id)
        if flow is None:
            raise PostRunVerificationError(f"TRACE_Flow {flow_id} does not exist.")
        if flow.status != "COMPLETED":
            raise PostRunVerificationError(
                f"Flow status is {flow.status}, expected COMPLETED."
            )

        summary = self.audit.summarize(flow_id)
        if not summary.complete:
            raise PostRunVerificationError(
                "Material audit chain is incomplete: "
                + ", ".join(summary.missing_stages)
            )

        unresolved = (
            self.session.query(models.ExecutionRecord)
            .filter(
                models.ExecutionRecord.flow_id == flow_id,
                models.ExecutionRecord.certainty_status == "UNKNOWN_OUTCOME",
            )
            .count()
        )
        if unresolved:
            raise PostRunVerificationError(
                f"{unresolved} execution(s) remain UNKNOWN_OUTCOME."
            )

        rejected = (
            self.session.query(models.ValidationResultRecord)
            .filter(
                models.ValidationResultRecord.flow_id == flow_id,
                models.ValidationResultRecord.result != "PASS",
            )
            .count()
        )
        if rejected:
            raise PostRunVerificationError(
                f"{rejected} validation result(s) were not PASS."
            )

        return {
            "status": "PASS",
            "flow_id": flow_id,
            "audit": asdict(summary),
            "unresolved_unknown_outcomes": unresolved,
            "non_pass_validations": rejected,
        }
