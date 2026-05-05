from __future__ import annotations

from src.observability.dashboard.services.trace_service import TraceService


def test_trace_service_parses_jsonl_and_filters(tmp_path):
    trace_file = tmp_path / "traces.jsonl"
    trace_file.write_text(
        "\n".join(
            [
                '{"trace_id": "q-1", "trace_type": "query", "started_at": "2026-05-01T10:00:00", "total_elapsed_ms": 100, "stages": [{"name": "dense_retrieval"}], "collection": "default"}',
                '{"trace_id": "i-1", "trace_type": "ingestion", "started_at": "2026-05-01T11:00:00", "total_elapsed_ms": 200, "stages": [{"name": "load"}], "source_path": "docs/manual.pdf"}',
            ]
        ),
        encoding="utf-8",
    )

    service = TraceService(str(trace_file))

    all_traces = service.list_traces()
    assert [trace["trace_id"] for trace in all_traces] == ["i-1", "q-1"]

    query_traces = service.list_traces("query")
    assert len(query_traces) == 1
    assert query_traces[0]["trace_id"] == "q-1"

    trace = service.get_trace("i-1")
    assert trace is not None
    assert trace["trace_type"] == "ingestion"

    summary = service.summarize()
    assert summary["trace_count"] == 2
    assert summary["stage_count"] == 2
    assert summary["total_latency_ms"] == 300.0
