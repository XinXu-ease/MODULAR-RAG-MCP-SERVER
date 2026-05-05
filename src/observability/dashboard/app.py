from __future__ import annotations

try:
    from .pages import (
        render_data_browser,
        render_evaluation_panel,
        render_ingestion_manager,
        render_ingestion_traces,
        render_overview,
        render_query_traces,
    )
except ImportError:
    from src.observability.dashboard.pages import (
        render_data_browser,
        render_evaluation_panel,
        render_ingestion_manager,
        render_ingestion_traces,
        render_overview,
        render_query_traces,
    )

PAGE_RENDERERS = [
    ("Overview", "overview", render_overview, True),
    ("Data Browser", "data-browser", render_data_browser, False),
    ("Ingestion Manager", "ingestion-manager", render_ingestion_manager, False),
    ("Ingestion Traces", "ingestion-traces", render_ingestion_traces, False),
    ("Query Traces", "query-traces", render_query_traces, False),
    ("Evaluation Panel", "evaluation-panel", render_evaluation_panel, False),
]


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Modular RAG Dashboard", layout="wide")
    page = st.navigation(
        [
            st.Page(renderer, title=title, url_path=url_path, default=is_default)
            for title, url_path, renderer, is_default in PAGE_RENDERERS
        ],
        position="sidebar",
        expanded=True,
    )
    page.run()


run = main


if __name__ == "__main__":
    main()
