from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import uuid4


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "qwen_rag_grounding_evaluation.py"
    spec = importlib.util.spec_from_file_location("qwen_rag_grounding_evaluation", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_step04d_cases_change_only_evidence_content():
    module = _load_script_module()

    assert [case.name for case in module.CASES] == ["POSITIVE", "NEGATIVE", "AMBIGUOUS"]
    assert len({case.documents for case in module.CASES}) == 3
    assert module.QUERY_TEXT

    measurements = module.neutral_measurements()
    assert measurements.last_price == 100.0
    assert measurements.return_1_period == 0.0
    assert measurements.momentum == 0.0


def test_step04d_each_case_indexes_only_its_own_instrument_evidence():
    module = _load_script_module()
    instrument_id = uuid4()

    for case in module.CASES:
        retrieval, docs = module.build_case_retrieval(case=case, instrument_id=instrument_id)
        assert len(docs) == 2
        assert all(doc.financial_instrument_id == instrument_id for doc in docs)
        assert all(doc.metadata["case"] == case.name for doc in docs)
        assert retrieval is not None
