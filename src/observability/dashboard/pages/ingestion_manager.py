from __future__ import annotations

import tempfile
from pathlib import Path

from src.ingestion.pipeline import IngestionPipeline

from ..services import DataService


def _persist_upload(uploaded_file) -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "modular_rag_dashboard_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / uploaded_file.name
    output_path.write_bytes(uploaded_file.getbuffer())
    return output_path


def render() -> None:
    import streamlit as st

    service = DataService()
    st.title("Ingestion Manager")
    st.caption("Trigger pipeline runs and monitor progress")

    uploaded_file = st.file_uploader("Upload a document", type=["pdf", "md", "markdown", "txt"])
    source_path = st.text_input("Or enter a local PDF path or website URL", value="")
    collection = st.text_input("Collection", value="default")
    force = st.checkbox("Force re-ingest", value=False)

    run_disabled = uploaded_file is None and not source_path.strip()

    if st.button("Start Ingestion", disabled=run_disabled):
        if uploaded_file is not None:
            source = str(_persist_upload(uploaded_file))
        else:
            source = source_path.strip()

        progress = st.progress(0.0)
        status = st.empty()

        def on_progress(stage_name: str, current: int, total: int) -> None:
            progress.progress(min(max(current / max(total, 1), 0.0), 1.0))
            status.write(f"{stage_name}: {current}/{total}")

        pipeline = IngestionPipeline(service.settings)
        result = pipeline.run(source=source, collection=collection, force=force, on_progress=on_progress)
        progress.progress(1.0)
        status.write("complete")

        if result.success:
            st.success(f"Ingestion finished: {result.metrics.total_chunks} chunks")
        else:
            st.error(result.error or "Ingestion failed")
