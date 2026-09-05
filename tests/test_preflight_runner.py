import pytest

from cats.runtime.preflight import PreflightRunner


def test_preflight_passes_when_all_dependencies_pass():
    p = PreflightRunner()
    p.check("db", lambda: "ok")
    p.check("broker", lambda: "ok")
    assert p.passed is True
    p.require_pass()


def test_preflight_fails_closed():
    p = PreflightRunner()
    p.check("db", lambda: "ok")

    def boom():
        raise RuntimeError("down")

    p.check("broker", boom)
    assert p.passed is False
    with pytest.raises(RuntimeError):
        p.require_pass()
