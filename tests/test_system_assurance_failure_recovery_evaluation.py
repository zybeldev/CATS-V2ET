from scripts.system_assurance_failure_recovery_evaluation import run_evaluation


def test_step07b_system_assurance_failure_recovery_passes():
    result = run_evaluation()
    assert result["result"] == "PASS"
    assert all(result["checks"].values())


def test_step07b_distinguishes_resolved_from_unresolved_reality():
    result = run_evaluation()
    assert result["resolved_broker_reality"]["recovered_certainty"] == "CONFIRMED"
    assert result["resolved_broker_reality"]["final_status"] == "COMPLETED"
    assert result["unresolved_broker_reality"]["recovered_certainty"] == "UNKNOWN_OUTCOME"
    assert result["unresolved_broker_reality"]["final_status"] == "SUSPENDED"
