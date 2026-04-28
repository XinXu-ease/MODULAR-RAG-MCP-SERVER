from src.core.query_engine.fusion import RRFFusion
from src.core.types import RetrievalResult


def _res(chunk_id, score, content="", metadata=None):
    return RetrievalResult(chunk_id=chunk_id, content=content, metadata=metadata or {}, score=score)


def test_rrf_fusion_is_deterministic():
    fusion = RRFFusion(k=60)

    dense = [_res("a", 0.9, "A"), _res("b", 0.8, "B")]
    sparse = [_res("b", 0.7, "B2"), _res("c", 0.6, "C")]

    out1 = fusion.fuse(dense_results=dense, sparse_results=sparse, top_k=3)
    out2 = fusion.fuse(dense_results=dense, sparse_results=sparse, top_k=3)

    assert [r.chunk_id for r in out1] == [r.chunk_id for r in out2]
    assert out1[0].chunk_id == "b"
    assert out1[0].score_breakdown["dense"] > 0
    assert out1[0].score_breakdown["sparse"] > 0
