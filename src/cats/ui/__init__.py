"""Human-facing observability and bounded PAPER execution-entry helpers for CATS V2ET."""

from .execution_entry import (
    StagedEvidence,
    build_paper_command,
    normalize_symbol,
    stage_local_evidence,
    validate_evidence_reference,
)
from .read_model import CatsUiReadModel, STAGE_TABLES

__all__ = [
    "CatsUiReadModel",
    "STAGE_TABLES",
    "StagedEvidence",
    "build_paper_command",
    "normalize_symbol",
    "stage_local_evidence",
    "validate_evidence_reference",
    "build_main_loop_command",
    "describe_launcher_failure",
    "main_loop_is_running",
    "probe_qwen_health",
    "qwen_health_url",
    "read_main_loop_status",
    "runtime_paths",
    "start_main_loop",
    "stop_main_loop",
    "tail_runtime_log",
]

from .system_control import (
    build_main_loop_command,
    describe_launcher_failure,
    main_loop_is_running,
    probe_qwen_health,
    qwen_health_url,
    read_main_loop_status,
    runtime_paths,
    start_main_loop,
    stop_main_loop,
    tail_runtime_log,
)
