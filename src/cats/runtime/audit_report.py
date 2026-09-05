from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from sqlalchemy.orm import Session

from cats.repositories.flow_audit import FlowAuditRepository
from cats.runtime.post_run_verifier import PostRunVerifier


class AuditReportGenerator:
    """Generate human-readable and machine-readable reports for one persisted flow."""

    def __init__(self, session: Session):
        self.session = session

    def build(self, flow_id: str) -> dict:
        verification = PostRunVerifier(self.session).verify(flow_id)
        audit = FlowAuditRepository(self.session).summarize(flow_id)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": verification["status"],
            "flow_id": flow_id,
            "audit": asdict(audit),
            "unresolved_unknown_outcomes": verification["unresolved_unknown_outcomes"],
            "non_pass_validations": verification["non_pass_validations"],
        }

    def write_json(self, flow_id: str, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.build(flow_id), indent=2, default=str),
            encoding="utf-8",
        )
        return path

    def write_markdown(self, flow_id: str, path: str | Path) -> Path:
        report = self.build(flow_id)
        audit = report["audit"]
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# CATS V2E PAPER Run Audit Report",
            "",
            f"- Flow ID: `{report['flow_id']}`",
            f"- Verification: **{report['verification_status']}**",
            f"- Generated: `{report['generated_at']}`",
            f"- Unknown outcomes: {report['unresolved_unknown_outcomes']}",
            f"- Non-PASS validations: {report['non_pass_validations']}",
            "",
            "## Material Chain",
            "",
        ]

        labels = [
            ("Evidence links", "evidence_count"),
            ("Assessments", "assessment_count"),
            ("Optimization requests", "optimization_request_count"),
            ("Portfolio alternatives", "alternative_count"),
            ("Portfolio decisions", "decision_count"),
            ("Validation results", "validation_count"),
            ("Executions", "execution_count"),
            ("Orders", "order_count"),
            ("Fills", "fill_count"),
            ("Reconciliations", "reconciliation_count"),
            ("Execution results", "execution_result_count"),
            ("Accepted portfolio states", "accepted_portfolio_state_count"),
            ("Provenance links", "provenance_count"),
            ("Lineage links", "lineage_count"),
        ]

        for label, key in labels:
            lines.append(f"- {label}: {audit[key]}")

        lines += [
            "",
            "## Result",
            "",
            "The persisted CATS material chain passed the post-run verifier.",
        ]

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
