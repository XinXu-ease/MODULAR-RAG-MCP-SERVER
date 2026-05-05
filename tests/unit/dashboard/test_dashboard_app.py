from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_dashboard_app_renders_from_streamlit_file_entrypoint():
    app = AppTest.from_file("src/observability/dashboard/app.py")

    app.run(timeout=30)

    assert not app.exception
    assert not app.radio
    assert app.title[0].value == "System Overview"
