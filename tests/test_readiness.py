from cats.runtime import ReadinessService


def test_readiness_requires_all_checks_to_pass():
    service = ReadinessService()
    service.run_check("one", lambda: "ok")
    service.run_check("two", lambda: "ok")
    assert service.ready is True


def test_readiness_fails_when_one_dependency_fails():
    service = ReadinessService()
    service.run_check("one", lambda: "ok")

    def fail():
        raise RuntimeError("not ready")

    service.run_check("two", fail)
    assert service.ready is False
