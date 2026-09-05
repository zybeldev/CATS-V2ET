from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load_module():
    path = SCRIPTS / "qwen_confidence_calibration_evaluation.py"
    spec = importlib.util.spec_from_file_location("qwen_confidence_calibration_evaluation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeDelegate:
    def __init__(self):
        self.last_metrics = None
        self.calls = []

    def reason(self, *, task: str, context: dict) -> dict:
        self.calls.append((task, context))
        return {"summary": "ok", "confidence": 0.5}


def test_step04e_wrapper_changes_only_task_instruction():
    module = _load_module()
    delegate = FakeDelegate()
    wrapper = module.ConfidenceCalibrationWrapper(delegate)
    context = {"retrieved_evidence": [{"text": "mixed evidence"}]}

    result = wrapper.reason(task="original task", context=context)

    assert result == {"summary": "ok", "confidence": 0.5}
    assert len(delegate.calls) == 1
    task_sent, context_sent = delegate.calls[0]
    assert task_sent.startswith("original task")
    assert module.CONFIDENCE_CALIBRATION_RULE in task_sent
    assert context_sent is context


def test_step04e_rule_distinguishes_evidentiary_certainty_from_uncertainty():
    module = _load_module()
    rule = module.CONFIDENCE_CALIBRATION_RULE.lower()

    assert "evidentiary" in rule
    assert "mixed" in rule
    assert "insufficiently directional" in rule
    assert "reduce confidence" in rule
    assert "not confidence that the situation is uncertain" in rule
