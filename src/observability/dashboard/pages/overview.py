from __future__ import annotations

from ..services import ConfigService, DataService


def render() -> None:
    import streamlit as st

    service = DataService()
    config_service = ConfigService(service.settings)
    overview = service.get_overview()
    snapshot = config_service.get_component_snapshot()

    st.title("System Overview")
    st.caption("Phase G dashboard shell")

    stats = overview["stats"]
    cols = st.columns(4)
    cols[0].metric("Documents", stats.get("document_count", 0))
    cols[1].metric("Chunks", stats.get("chunk_count", 0))
    cols[2].metric("Images", stats.get("image_count", 0))
    cols[3].metric("Traces", overview["trace_summary"].get("trace_count", 0))

    st.subheader("Component Snapshot")
    st.json(snapshot)

    st.subheader("Collections")
    st.table(overview["collections"])

    st.subheader("Trace Summary")
    st.json(overview["trace_summary"])
