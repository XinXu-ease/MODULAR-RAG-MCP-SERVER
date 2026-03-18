from src.libs.evaluator.evaluator_factory import create_evaluator
from src.libs.evaluator.base import BaseEvaluator


def test_create_evaluator_is_base():
    ev = create_evaluator()
    assert isinstance(ev, BaseEvaluator)
    metrics = ev.evaluate("q", [], "ans")
    assert isinstance(metrics, dict)
    assert metrics.get("dummy") is True
