from __future__ import annotations

from ..services import TraceService


def render() -> None:
    import streamlit as st

    service = TraceService()
    traces = service.list_traces("ingestion")

    st.title("Ingestion Traces")
    st.caption("Inspect load, split, transform, embed, and upsert stages")
    st.table([
        {
            "trace_id": trace.get("trace_id"),
            "started_at": trace.get("started_at"),
            "elapsed_ms": trace.get("total_elapsed_ms") or trace.get("elapsed_ms") or 0,
            "source": trace.get("source") or trace.get("source_path"),
        }
        for trace in traces
    ])

    if not traces:
        st.info("No ingestion traces found.")
        return

    selected_trace_id = st.selectbox("Trace", [trace["trace_id"] for trace in traces])
    trace = service.get_trace(selected_trace_id) or {}

    st.json(trace)
