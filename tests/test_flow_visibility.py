from uuid import uuid4

from cats.runtime.flow_visibility import FlowVisibilityBuilder


def test_flow_visibility_is_both_structured_and_operator_readable():
    flow_id = uuid4()
    builder = FlowVisibilityBuilder(flow_id=flow_id, symbol="AAPL")
    builder.stage(
        "INPUT / EVIDENCE",
        items=[{
            "source": "Example News",
            "source_date": "2026-09-01T10:00:00+00:00",
            "freshness_status": "RECENT_7D",
        }],
    )
    builder.stage(
        "PMA DECISION",
        decision_type="BUY_OR_INCREASE",
        required_quantity_delta=-0.25,
        delta_side="SELL",
    )
    report = builder.build(outcome="COMPLETED")

    payload = report.as_dict()
    assert payload["flow_id"] == str(flow_id)
    assert payload["stages"][0]["details"]["items"][0]["freshness_status"] == "RECENT_7D"

    text = report.render_text()
    assert "CATS FLOW — AAPL" in text
    assert "INPUT / EVIDENCE" in text
    assert "PMA DECISION" in text
    assert "Delta Side: SELL" in text
