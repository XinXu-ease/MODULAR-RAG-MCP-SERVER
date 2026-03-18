from src.libs.reranker.reranker_factory import create_reranker
from src.libs.reranker.base import BaseReranker


def test_create_reranker_is_base():
    r = create_reranker()
    assert isinstance(r, BaseReranker)
    candidates = [{"id": 1}, {"id": 2}]
    assert r.rerank("q", candidates) == candidates
