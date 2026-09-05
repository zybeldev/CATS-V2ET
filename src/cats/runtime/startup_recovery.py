from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from cats.database import models
from cats.runtime.production_paper_recovery import ProductionPaperRecovery


RECOVERABLE_FLOW_STATUSES = {"ACTIVE", "SUSPENDED"}
TERMINAL_FLOW_STATUSES = {"COMPLETED", "FAILED", "TERMINATED"}


def recover_outstanding_paper_flows(*, session: Session, broker) -> dict[str, Any]:
    """Reconcile persisted non-terminal PAPER flows before normal runtime starts.

    Startup recovery never creates a replacement flow and never submits a new order.
    It delegates each existing recoverable flow to ProductionPaperRecovery, which
    reconciles the persisted execution identity against broker-confirmed reality.
    Normal autonomous work may start only when every discovered non-terminal
    PRODUCTION_PAPER flow is resolved.
    """

    flows = (
        session.query(models.TraceFlow)
        .filter(models.TraceFlow.flow_type == "PRODUCTION_PAPER")
        .order_by(models.TraceFlow.started_at.asc())
        .all()
    )

    non_terminal = [
        row for row in flows
        if str(row.status or "").upper() not in TERMINAL_FLOW_STATUSES
    ]
    if not non_terminal:
        return {
            "status": "CLEAR",
            "checked_flow_count": 0,
            "recovered_flow_count": 0,
            "unresolved_flow_count": 0,
            "flows": [],
            "detail": "No non-terminal PRODUCTION_PAPER flow required startup reconciliation.",
        }

    details: list[dict[str, Any]] = []
    recovered_count = 0
    unresolved_count = 0

    for flow in non_terminal:
        flow_id = str(flow.flow_id)
        prior_status = str(flow.status or "").upper()

        if prior_status not in RECOVERABLE_FLOW_STATUSES:
            unresolved_count += 1
            details.append(
                {
                    "flow_id": flow_id,
                    "previous_status": prior_status,
                    "status": "BLOCKED",
                    "completed": False,
                    "diagnostics": [
                        f"Flow status {prior_status!r} is non-terminal but is not an allowed automatic recovery state."
                    ],
                }
            )
            continue

        try:
            result = ProductionPaperRecovery(session=session, broker=broker).recover(UUID(flow_id))
        except Exception as exc:
            session.rollback()
            unresolved_count += 1
            details.append(
                {
                    "flow_id": flow_id,
                    "previous_status": prior_status,
                    "status": "FAILED",
                    "completed": False,
                    "diagnostics": [f"{type(exc).__name__}: {exc}"],
                }
            )
            continue

        if result.completed:
            recovered_count += 1
            state = "COMPLETED"
        else:
            unresolved_count += 1
            state = "SUSPENDED"

        details.append(
            {
                "flow_id": flow_id,
                "previous_status": prior_status,
                "status": state,
                "completed": bool(result.completed),
                "accepted_portfolio_state_id": (
                    None
                    if result.accepted_portfolio_state_id is None
                    else str(result.accepted_portfolio_state_id)
                ),
                "execution_ids": [str(value) for value in result.execution_ids],
                "diagnostics": list(result.diagnostics),
            }
        )

    status = "COMPLETED" if unresolved_count == 0 else "BLOCKED"
    if status == "COMPLETED":
        detail = (
            f"Startup reconciliation completed {recovered_count} existing PAPER flow(s); "
            "normal autonomous operation may start."
        )
    else:
        detail = (
            f"Startup reconciliation left {unresolved_count} PAPER flow(s) unresolved; "
            "normal autonomous operation is blocked."
        )

    return {
        "status": status,
        "checked_flow_count": len(non_terminal),
        "recovered_flow_count": recovered_count,
        "unresolved_flow_count": unresolved_count,
        "flows": details,
        "detail": detail,
    }
