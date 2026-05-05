from __future__ import annotations

from ..services import TraceService


def render() -> None:
    import streamlit as st

    service = TraceService()
    traces = service.list_traces("query")

    st.title("Query Traces")
    st.caption("Inspect dense, sparse, fusion, and rerank stages")
    st.table([
        {
            "trace_id": trace.get("trace_id"),
            "started_at": trace.get("started_at"),
            "elapsed_ms": trace.get("total_elapsed_ms") or trace.get("elapsed_ms") or 0,
            "query": trace.get("query") or trace.get("user_query"),
        }
        for trace in traces
    ])

    if not traces:
        st.info("No query traces found.")
        return

    selected_trace_id = st.selectbox("Trace", [trace["trace_id"] for trace in traces])
    trace = service.get_trace(selected_trace_id) or {}

    st.json(trace)
