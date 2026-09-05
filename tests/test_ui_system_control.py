from pathlib import Path

from cats.ui.system_control import (
    build_main_loop_command,
    describe_launcher_failure,
    qwen_health_url,
    runtime_paths,
)


def test_qwen_health_url_replaces_reason_path():
    assert (
        qwen_health_url("https://example.trycloudflare.com/reason")
        == "https://example.trycloudflare.com/health"
    )


def test_runtime_paths_are_bounded_under_project_root(tmp_path: Path):
    paths = runtime_paths(tmp_path)
    assert paths.status == tmp_path / ".cats_runtime" / "main_loop_status.json"
    assert paths.pid == tmp_path / ".cats_runtime" / "main_loop.pid"
    assert paths.stop == tmp_path / ".cats_runtime" / "main_loop.stop"


def test_build_main_loop_command_uses_current_python_and_runtime_paths(tmp_path: Path):
    command = build_main_loop_command(tmp_path)
    assert command[0]
    assert command[1].endswith("scripts/cats_main_loop.py")
    assert "--status-file" in command
    assert "--pid-file" in command
    assert "--stop-file" in command


def test_descriptive_qwen_launcher_failure():
    message = describe_launcher_failure(
        "RuntimeError: Remote Qwen endpoint is unavailable: [Errno -2] Name or service not known",
        1,
    )
    assert "remote Qwen endpoint is unavailable" in message
    assert "Colab" in message


def test_descriptive_http_403_launcher_failure():
    message = describe_launcher_failure("urllib.error.HTTPError: HTTP Error 403: Forbidden", 1)
    assert "HTTP 403" in message
    assert "Local File" in message
