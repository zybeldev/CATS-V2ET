import importlib.util
from pathlib import Path


def _load_script():
    path = Path(__file__).parents[1] / "scripts" / "gpt_oss_taa_comparative_evaluation.py"
    spec = importlib.util.spec_from_file_location("gpt_oss_eval", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gpt_oss_comparison_reuses_qwen_controlled_evidence_cases():
    module = _load_script()
    assert [case.name for case in module.step04d.CASES] == ["POSITIVE", "NEGATIVE", "AMBIGUOUS"]
    assert "Mixed, contradictory" in module.CONFIDENCE_CALIBRATION_RULE


def test_calibration_rule_requires_ambiguous_not_above_directional_cases():
    module = _load_script()
    assert module._calibration_pass({"positive": 0.8, "negative": 0.7, "ambiguous": 0.4}) is True
    assert module._calibration_pass({"positive": 0.8, "negative": 0.3, "ambiguous": 0.5}) is False


def test_gpt_oss_comparison_makes_existing_numeric_confidence_contract_explicit():
    module = _load_script()
    rule = module.NUMERIC_CONFIDENCE_CONTRACT_RULE
    assert "JSON number" in rule
    assert "0.0 and 1.0" in rule
    assert "low, medium, or high" in rule


def test_gpt_oss_wrapper_sends_calibration_and_numeric_contract_rules():
    module = _load_script()

    class FakeDelegate:
        last_metrics = None

        def __init__(self):
            self.task = None

        def reason(self, *, task, context):
            self.task = task
            return {"summary": "ok", "confidence": 0.5}

    delegate = FakeDelegate()
    wrapped = module.ConfidenceCalibrationWrapper(delegate)
    result = wrapped.reason(task="base task", context={})

    assert result["confidence"] == 0.5
    assert module.CONFIDENCE_CALIBRATION_RULE in delegate.task
    assert module.NUMERIC_CONFIDENCE_CONTRACT_RULE in delegate.task
