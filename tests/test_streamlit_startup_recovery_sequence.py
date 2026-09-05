from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_recovery_entrypoint_has_no_qwen_dependency():
    source = (_project_root() / "scripts" / "cats_startup_recovery.py").read_text(encoding="utf-8")
    upper = source.upper()
    assert "QWEN" not in upper
    assert "REMOTEQWEN" not in upper
    assert "RECOVER_OUTSTANDING_PAPER_FLOWS" in upper


def test_streamlit_load_sequence_runs_recovery_before_qwen_gate():
    source = (_project_root() / "scripts" / "streamlit_dashboard.py").read_text(encoding="utf-8")
    start = source.index('if st.session_state.pop("cats_sidebar_load_requested", False):')
    end = source.index('if st.session_state.get("cats_last_startup_recovery_output"):', start)
    block = source[start:end]

    recovery_pos = block.index("run_startup_recovery(project_root)")
    qwen_pos = block.index("elif not qwen_ready:")
    assert recovery_pos < qwen_pos


def test_streamlit_recovery_precedes_new_work_authorization():
    source = (_project_root() / "scripts" / "streamlit_dashboard.py").read_text(encoding="utf-8")
    start = source.index('if st.session_state.pop("cats_sidebar_load_requested", False):')
    end = source.index('if st.session_state.get("cats_last_startup_recovery_output"):', start)
    block = source[start:end]

    recovery_pos = block.index("run_startup_recovery(project_root)")
    authorization_pos = block.index("paper_execution_enabled and not auto_confirm")
    assert recovery_pos < authorization_pos
