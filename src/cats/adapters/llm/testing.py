from __future__ import annotations


class DeterministicAssessmentModel:
    """Test-only structured reasoning model.

    It proves the TAA integration path without pretending to be a production
    LLM. Production model adapters are added separately.
    """

    def reason(self, *, task: str, context: dict) -> dict:
        evidence = context["retrieved_evidence"]
        measurements = context["deterministic_measurements"]
        symbol = context["authoritative_context"]["symbol"]
        if evidence:
            lead = evidence[0]["text"][:180]
            summary = (
                f"{symbol}: retrieved evidence indicates {lead}. "
                f"Last price={measurements['last_price']:.2f}; "
                f"momentum={measurements['momentum']}."
            )
            confidence = min(0.9, 0.5 + 0.08 * len(evidence))
            momentum = measurements.get("momentum")
            outlook = "FAVORABLE" if momentum is not None and momentum > 0 else "NEUTRAL"
        else:
            summary = f"{symbol}: insufficient retrieved evidence for a grounded assessment."
            confidence = 0.2
            outlook = "NEUTRAL"
        return {
            "outlook": outlook,
            "summary": summary,
            "confidence": confidence,
            "valid_for_minutes": 60,
        }
