import pytest

from src.ingestion.loaders.web_loader import WebLoader


class DummyResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class DummySession:
    def __init__(self, html: str):
        self.html = html
        self.headers = {}

    def get(self, source: str, timeout: int):
        return DummyResponse(self.html)


def test_web_loader_loads_whitelisted_page():
    html = """
    <html>
      <head><title>V60 Recipe</title></head>
      <body>
        <h1>V60 Recipe</h1>
        <p>Use 15g coffee.</p>
        <ul><li>Bloom 30 seconds</li></ul>
        <img src="https://example.com/v60.png" />
      </body>
    </html>
    """
    loader = WebLoader(session=DummySession(html))
    document = loader.load("https://www.hariousa.com/recipes/v60")

    assert document.metadata["doc_type"] == "website"
    assert document.metadata["website_name"] == "Hario USA"
    assert document.metadata["page_type"] == "recipe"
    assert "Use 15g coffee." in document.text
    assert document.metadata["images"] == ["https://example.com/v60.png"]


def test_web_loader_rejects_non_whitelisted_url():
    loader = WebLoader(session=DummySession("<html></html>"))
    with pytest.raises(ValueError):
        loader.load("https://example.com/random")
