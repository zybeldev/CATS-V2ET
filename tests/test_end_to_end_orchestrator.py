from cats.runtime.demo import run_demo


def test_complete_vertical_slice_demo():
    result = run_demo()
    assert result.completed is True
    assert len(result.execution_ids) == 1
